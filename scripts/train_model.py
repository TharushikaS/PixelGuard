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
def build_dataset(
    image_dir: str,
    image_size: int,
    batch_size: int,
    message_length: int,
    shuffle_buffer: int = 1024,
) -> tf.data.Dataset:
    """
    A `tf.data.Dataset` that yields (cover, message) pairs.

    Supports any folder of jpg/jpeg/png files. Images are randomly
    cropped + resized to image_size×image_size and normalized to [0, 1].
    Messages are random bits drawn fresh for every example.
    """
    patterns = [
        os.path.join(image_dir, "*.jpg"),
        os.path.join(image_dir, "*.jpeg"),
        os.path.join(image_dir, "*.png"),
    ]
    files = tf.data.Dataset.list_files(patterns, shuffle=True)

    def _load(path):
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

    return (
        files
        .repeat()
        .map(_load, num_parallel_calls=tf.data.AUTOTUNE)
        .batch(batch_size, drop_remainder=True)
        .prefetch(tf.data.AUTOTUNE)
    )


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

            L_M = self.bce_logits(message, decoded_logits)
            L_I = tf.reduce_mean(tf.square(cover - stego))

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
        pred = tf.cast(tf.sigmoid(decoded_logits) > 0.5, tf.float32)
        bit_acc = tf.reduce_mean(
            tf.cast(tf.equal(pred, message), tf.float32)
        )

        # PSNR on the (un-noised) stego — quick training signal.
        mse = tf.reduce_mean(tf.square(cover - stego))
        psnr = 10.0 * (tf.math.log(1.0 / (mse + 1e-12)) / tf.math.log(10.0))

        return {
            "L_M": L_M, "L_I": L_I, "L_G": L_G, "L_D": L_D,
            "bit_acc": bit_acc, "psnr": psnr,
        }

    # ------------------------------------------------------------------
    def fit(self, dataset, epochs: int, steps_per_epoch: int):
        ds_iter = iter(dataset)
        for epoch in range(1, epochs + 1):
            t0 = time.time()
            agg = {k: 0.0 for k in ["L_M", "L_I", "L_G", "L_D", "bit_acc", "psnr"]}

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
                        f"PSNR={float(m['psnr']):.1f}dB"
                    )

            for k in agg:
                agg[k] /= steps_per_epoch

            print(
                f"[epoch {epoch:3d}] time={time.time() - t0:.1f}s  "
                f"L_M={agg['L_M']:.4f} L_I={agg['L_I']:.4f} "
                f"L_G={agg['L_G']:.4f} L_D={agg['L_D']:.4f} "
                f"bit_acc={agg['bit_acc']*100:.2f}% PSNR={agg['psnr']:.2f}dB"
            )

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
        "--noise-mode",
        default="identity",
        choices=["identity", "combined", "dropout", "cropout", "crop", "gaussian", "jpeg_mask"],
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

    dataset = build_dataset(
        args.image_dir,
        image_size=args.image_size,
        batch_size=args.batch_size,
        message_length=args.message_length,
    )

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

    trainer.fit(dataset, epochs=args.epochs, steps_per_epoch=args.steps_per_epoch)
    print("Training complete.")


if __name__ == "__main__":
    main()
