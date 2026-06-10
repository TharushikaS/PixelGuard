#!/usr/bin/env python3
"""
Train the HiDDeN-style encoder + decoder + discriminator on a folder of
images (e.g. COCO 2017 train2017).

Usage (local GPU or Colab):

    python scripts/train_model.py \\
        --image-dir /path/to/coco/train2017 \\
        --image-size 128 \\
        --message-length 32 \\
        --batch-size 12 \\
        --epochs 200 \\
        --model-dir ./models

Curriculum: the noise layer randomly picks one of {identity, dropout,
cropout, crop, gaussian, jpeg_mask} per minibatch. This is the "combined
model" recipe from Section 4.2 of Zhu et al. 2018.

Checkpoints (encoder/decoder/discriminator) are saved to MODEL_DIR after
every epoch. Sample stego images are written to MODEL_DIR/samples/ each
epoch for visual inspection.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import tensorflow as tf

# Allow `python scripts/train_model.py` to import the backend package.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import (  # noqa: E402
    CombinedNoiseLayer,
    Decoder,
    Discriminator,
    Encoder,
    NoiseLayer,
)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
def _load_image_for_training(image_size: int):
    """Returns a tf.function-compatible loader: path -> (img, random_msg)."""
    def _load(path, message_length: int):
        raw = tf.io.read_file(path)
        img = tf.io.decode_image(raw, channels=3, expand_animations=False)
        img.set_shape([None, None, 3])
        img = tf.image.resize_with_crop_or_pad(
            img,
            tf.maximum(tf.shape(img)[0], image_size),
            tf.maximum(tf.shape(img)[1], image_size),
        )
        img = tf.image.random_crop(img, (image_size, image_size, 3))
        img = tf.cast(img, tf.float32) / 255.0
        msg = tf.cast(
            tf.random.uniform((message_length,), 0, 2, dtype=tf.int32),
            tf.float32,
        )
        return img, msg
    return _load


def _list_image_paths(image_dir: str) -> list:
    """All jpg/jpeg/png paths in a folder, sorted for reproducibility."""
    patterns = ("*.jpg", "*.jpeg", "*.png")
    paths = []
    for pat in patterns:
        paths += tf.io.gfile.glob(os.path.join(image_dir, pat))
    paths.sort()
    return paths


def build_datasets(
    image_dir: str,
    image_size: int,
    batch_size: int,
    message_length: int,
    val_split: float = 0.1,
) -> tuple[tf.data.Dataset, tf.data.Dataset, int, int]:
    """
    Split the image folder into TRAIN and TEST sets, then build a
    tf.data.Dataset for each.

    Returns:
        (train_ds, test_ds, n_train, n_test)

    Each dataset yields (cover, message) pairs where message is a freshly
    sampled random bit string per example. The test split is held out
    from training entirely.
    """
    all_paths = _list_image_paths(image_dir)
    if not all_paths:
        raise FileNotFoundError(f"No images found under {image_dir}")

    n_test = max(1, int(len(all_paths) * val_split))
    n_train = len(all_paths) - n_test

    # Stable, deterministic split: last `n_test` paths after sort = test set.
    train_paths = all_paths[:n_train]
    test_paths = all_paths[n_train:]

    loader = _load_image_for_training(image_size)

    train_ds = (
        tf.data.Dataset.from_tensor_slices(train_paths)
        .shuffle(min(len(train_paths), 4096), reshuffle_each_iteration=True)
        .repeat()
        .map(lambda p: loader(p, message_length), num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size, drop_remainder=True)
        .prefetch(tf.data.AUTOTUNE)
    )

    test_ds = (
        tf.data.Dataset.from_tensor_slices(test_paths)
        .map(lambda p: loader(p, message_length), num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size, drop_remainder=False)
        .prefetch(tf.data.AUTOTUNE)
    )

    return train_ds, test_ds, n_train, n_test


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------
class HiDDeNTrainer:
    def __init__(
        self,
        message_length: int = 32,
        image_size: int = 128,
        lambda_I: float = 0.7,           # image-distortion loss weight (paper)
        lambda_G: float = 0.001,         # adversarial loss weight (paper)
        lr_encdec: float = 1e-3,
        lr_disc: float = 1e-3,
        model_dir: str = "./models",
        noise_mode: str = "identity",    # "identity" | "combined" | a NoiseLayer kind
    ):
        self.message_length = message_length
        self.image_size = image_size
        self.lambda_I = lambda_I
        self.lambda_G = lambda_G
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        (self.model_dir / "samples").mkdir(exist_ok=True)

        # Networks
        self.encoder = Encoder(message_length=message_length)
        self.decoder = Decoder(message_length=message_length)
        self.discriminator = Discriminator()

        # Noise layer selection. Curriculum recipe:
        #   Phase 1 — "identity" (no distortion) for ~20-30 epochs to lock
        #             in the encoder/decoder cycle.
        #   Phase 2 — "combined" for 20-50 more epochs to harden against
        #             JPEG / blur / crop / resize.
        if noise_mode == "combined":
            self.noise_layer = CombinedNoiseLayer()
        else:
            self.noise_layer = NoiseLayer(kind=noise_mode)
        self.noise_mode = noise_mode

        # Optimizers — paper trains encoder+decoder together w/ one Adam,
        # discriminator separately.
        self.opt_encdec = tf.keras.optimizers.Adam(lr_encdec)
        self.opt_disc = tf.keras.optimizers.Adam(lr_disc)

        self.bce_logits = tf.keras.losses.BinaryCrossentropy(from_logits=True)

    # ------------------------------------------------------------------
    @tf.function
    def train_step(self, cover, message):
        # ---------------- Phase 1: encoder + decoder ----------------
        with tf.GradientTape() as tape:
            stego = self.encoder([cover, message], training=True)

            # Pass-through noise (chosen randomly each minibatch).
            noisy = self.noise_layer(cover, stego, training=True)

            # If the noise layer cropped, the decoder still works thanks
            # to GAP. No resize needed.
            decoded_logits = self.decoder(noisy, training=True)
            disc_on_stego = self.discriminator(stego, training=False)

            # Paper §3: L_M = ||M_in - M_out||^2 / L  (mean squared error).
            # We use sigmoid(logits) so predictions are in [0, 1] like the
            # target bits {0, 1}. MSE keeps L_M numerically comparable to
            # L_I (both in roughly the same scale), letting λ_I = 0.7
            # actually balance message and image objectives as designed.
            decoded_probs = tf.sigmoid(decoded_logits)
            L_M = tf.reduce_mean(tf.square(message - decoded_probs))

            # Proposal §4.2-4.3: weighted per-channel MSE in YCbCr space +
            # SSIM. Penalize luminance (Y) perturbations more than chroma
            # (Cb, Cr) because humans see luminance differences more
            # acutely. This pushes the encoder away from green-dominant
            # embeddings (RGB MSE treats all channels equally; YCbCr MSE
            # respects human perception).
            yuv_cover = tf.image.rgb_to_yuv(cover)
            yuv_stego = tf.image.rgb_to_yuv(stego)
            mse_y  = tf.reduce_mean(tf.square(yuv_cover[..., 0:1] - yuv_stego[..., 0:1]))
            mse_uv = tf.reduce_mean(tf.square(yuv_cover[..., 1:]  - yuv_stego[..., 1:]))
            # 4:1 weighting follows JPEG chroma-subsampling intuition.
            mse = 4.0 * mse_y + 1.0 * mse_uv

            ssim = tf.reduce_mean(tf.image.ssim(cover, stego, max_val=1.0))
            L_I = mse + (1.0 - ssim)

            # Encoder wants disc(stego) → 1 (i.e. "this is a cover").
            L_G = self.bce_logits(
                tf.ones_like(disc_on_stego), disc_on_stego
            )
            L_enc = L_M + self.lambda_I * L_I + self.lambda_G * L_G

        vars_encdec = (
            self.encoder.trainable_variables
            + self.decoder.trainable_variables
        )
        grads = tape.gradient(L_enc, vars_encdec)
        self.opt_encdec.apply_gradients(zip(grads, vars_encdec))

        # ---------------- Phase 2: discriminator ----------------
        with tf.GradientTape() as tape:
            stego_d = self.encoder([cover, message], training=False)
            d_cover = self.discriminator(cover, training=True)
            d_stego = self.discriminator(stego_d, training=True)
            # cover → label 1 ("real"), stego → label 0 ("fake")
            L_D = (
                self.bce_logits(tf.ones_like(d_cover), d_cover)
                + self.bce_logits(tf.zeros_like(d_stego), d_stego)
            )

        grads = tape.gradient(L_D, self.discriminator.trainable_variables)
        self.opt_disc.apply_gradients(
            zip(grads, self.discriminator.trainable_variables)
        )

        # ---------------- Metrics ----------------
        pred = tf.cast(decoded_probs > 0.5, tf.float32)
        bit_acc = tf.reduce_mean(
            tf.cast(tf.equal(pred, message), tf.float32)
        )

        # PSNR on the (un-noised) stego — quick training signal.
        mse = tf.reduce_mean(tf.square(cover - stego))
        psnr = 10.0 * (tf.math.log(1.0 / (mse + 1e-12)) / tf.math.log(10.0))

        return {
            "L_M": L_M, "L_I": L_I, "L_G": L_G, "L_D": L_D,
            "bit_acc": bit_acc, "psnr": psnr, "ssim": ssim,
        }

    # ------------------------------------------------------------------
    @tf.function
    def eval_step(self, cover, message):
        """Forward pass only — no gradient updates. Used on the test set."""
        stego = self.encoder([cover, message], training=False)
        # No noise on test — measure clean encode/decode roundtrip.
        decoded_logits = self.decoder(stego, training=False)

        pred = tf.cast(tf.sigmoid(decoded_logits) > 0.5, tf.float32)
        bit_acc = tf.reduce_mean(tf.cast(tf.equal(pred, message), tf.float32))

        mse = tf.reduce_mean(tf.square(cover - stego))
        psnr = 10.0 * (tf.math.log(1.0 / (mse + 1e-12)) / tf.math.log(10.0))
        ssim = tf.reduce_mean(tf.image.ssim(cover, stego, max_val=1.0))
        return bit_acc, psnr, ssim

    def evaluate(self, test_ds):
        """Compute test bit_acc / PSNR / SSIM over the entire held-out set."""
        sum_acc = sum_psnr = sum_ssim = 0.0
        n_batches = 0
        for cover, msg in test_ds:
            ba, psnr, ssim = self.eval_step(cover, msg)
            sum_acc += float(ba.numpy())
            sum_psnr += float(psnr.numpy())
            sum_ssim += float(ssim.numpy())
            n_batches += 1
        if n_batches == 0:
            return None
        return {
            "bit_acc": sum_acc / n_batches,
            "psnr":    sum_psnr / n_batches,
            "ssim":    sum_ssim / n_batches,
        }

    # ------------------------------------------------------------------
    def fit(self, dataset, epochs: int, steps_per_epoch: int, test_ds=None):
        ds_iter = iter(dataset)
        for epoch in range(1, epochs + 1):
            t0 = time.time()
            agg = {k: 0.0 for k in ["L_M", "L_I", "L_G", "L_D", "bit_acc", "psnr", "ssim"]}

            for step in range(steps_per_epoch):
                cover, msg = next(ds_iter)
                m = self.train_step(cover, msg)
                for k, v in m.items():
                    agg[k] += float(v.numpy())

                if step % 50 == 0:
                    print(
                        f"  ep {epoch:3d} step {step:4d}/{steps_per_epoch} "
                        f"L_M={float(m['L_M']):.4f} L_I={float(m['L_I']):.4f} "
                        f"bit_acc={float(m['bit_acc'])*100:.1f}% "
                        f"PSNR={float(m['psnr']):.1f}dB "
                        f"SSIM={float(m['ssim']):.4f}"
                    )

            for k in agg:
                agg[k] /= steps_per_epoch

            line = (
                f"[epoch {epoch:3d}] time={time.time() - t0:.1f}s  "
                f"L_M={agg['L_M']:.4f} L_I={agg['L_I']:.4f} "
                f"L_G={agg['L_G']:.4f} L_D={agg['L_D']:.4f} "
                f"train: bit_acc={agg['bit_acc']*100:.2f}% "
                f"PSNR={agg['psnr']:.2f}dB SSIM={agg['ssim']:.4f}"
            )

            # Evaluate on the held-out test set (no noise, no grads).
            if test_ds is not None:
                test_metrics = self.evaluate(test_ds)
                if test_metrics is not None:
                    line += (
                        f"   | test: bit_acc={test_metrics['bit_acc']*100:.2f}% "
                        f"PSNR={test_metrics['psnr']:.2f}dB SSIM={test_metrics['ssim']:.4f}"
                    )
            print(line)

            self.save_checkpoint(epoch, cover, msg)

    # ------------------------------------------------------------------
    def save_checkpoint(self, epoch: int, cover_batch, msg_batch):
        """Save weights + a sample stego image for visual inspection."""
        # Keras 3 (TF 2.16+) requires the .weights.h5 suffix.
        self.encoder.save_weights(str(self.model_dir / "encoder.weights.h5"))
        self.decoder.save_weights(str(self.model_dir / "decoder.weights.h5"))
        self.discriminator.save_weights(str(self.model_dir / "discriminator.weights.h5"))

        # Sample image
        stego = self.encoder([cover_batch, msg_batch], training=False).numpy()
        cover = cover_batch.numpy()
        # Save a 2-row strip: [cover | stego | 10×|stego-cover|]
        diff = np.clip(10.0 * np.abs(stego - cover), 0, 1)
        strip = np.concatenate([cover[0], stego[0], diff[0]], axis=1)
        strip_u8 = (strip * 255).clip(0, 255).astype(np.uint8)

        try:
            from PIL import Image
            Image.fromarray(strip_u8).save(
                self.model_dir / "samples" / f"epoch_{epoch:03d}.png"
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  (could not save sample: {exc})")

        print(f"  ✓ checkpoint saved to {self.model_dir}")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image-dir", required=True, help="Folder of training images")
    parser.add_argument("--image-size", type=int, default=128)
    parser.add_argument("--message-length", type=int, default=32)
    parser.add_argument("--batch-size", type=int, default=12)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--steps-per-epoch", type=int, default=500)
    parser.add_argument("--lambda-i", type=float, default=0.7)
    parser.add_argument("--lambda-g", type=float, default=0.001)
    parser.add_argument("--lr-encdec", type=float, default=1e-3)
    parser.add_argument("--lr-disc", type=float, default=1e-3)
    parser.add_argument("--model-dir", default="./models")
    parser.add_argument(
        "--val-split", type=float, default=0.1,
        help="Fraction of images held out for test/validation (default 0.1 = 10%%)",
    )
    parser.add_argument(
        "--noise-mode",
        default="identity",
        choices=["identity", "combined", "dropout", "cropout", "crop", "gaussian", "jpeg_mask", "jpeg_drop"],
        help=(
            "Distortion applied during training. 'identity' is the right "
            "choice for the first warm-up run (fast convergence). Use "
            "'combined' or a specific kind once basic encode/decode works."
        ),
    )
    args = parser.parse_args()

    # Report device info up front.
    gpus = tf.config.list_physical_devices("GPU")
    if gpus:
        print(f"GPU(s) detected: {[g.name for g in gpus]}")
        try:
            for g in gpus:
                tf.config.experimental.set_memory_growth(g, True)
        except RuntimeError:
            pass
    else:
        print("No GPU detected — training on CPU will be SLOW.")

    train_ds, test_ds, n_train, n_test = build_datasets(
        args.image_dir,
        image_size=args.image_size,
        batch_size=args.batch_size,
        message_length=args.message_length,
        val_split=args.val_split,
    )
    print(f"[data] {n_train} training images, {n_test} held-out test images")

    trainer = HiDDeNTrainer(
        message_length=args.message_length,
        image_size=args.image_size,
        lambda_I=args.lambda_i,
        lambda_G=args.lambda_g,
        lr_encdec=args.lr_encdec,
        lr_disc=args.lr_disc,
        model_dir=args.model_dir,
        noise_mode=args.noise_mode,
    )
    print(f"[train] noise_mode={args.noise_mode}")

    trainer.fit(
        train_ds,
        epochs=args.epochs,
        steps_per_epoch=args.steps_per_epoch,
        test_ds=test_ds,
    )
    print("Training complete.")


if __name__ == "__main__":
    main()
