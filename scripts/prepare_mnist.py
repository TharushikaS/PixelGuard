#!/usr/bin/env python3
"""
Prepare MNIST as RGB PNG images for HiDDeN training.

Converts the 28×28 grayscale digits into 32×32 RGB PNGs and writes them
to a folder. The training script can then consume them via --image-dir
like any other photo dataset.

Why 32×32 (not 28×28):
  The differentiable JPEG-Mask noise layer uses 8×8 DCT blocks and
  needs the side to be a multiple of 8.

Why RGB:
  The encoder/decoder expect 3-channel input per the paper. We tile the
  grayscale channel 3 times — gives the network the same shape but with
  identical R = G = B values.

Usage:
    python scripts/prepare_mnist.py --out-dir ./mnist_images --n-samples 10000
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import tensorflow as tf
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="./mnist_images")
    p.add_argument("--n-samples", type=int, default=10000,
                   help="How many MNIST images to dump (max 70 000)")
    p.add_argument("--image-size", type=int, default=32,
                   help="Output image side; must be multiple of 8")
    args = p.parse_args()

    if args.image_size % 8 != 0:
        raise SystemExit(
            f"--image-size must be a multiple of 8 (got {args.image_size})"
        )

    os.makedirs(args.out_dir, exist_ok=True)

    print("Downloading MNIST (cached in ~/.keras/ after first run)…")
    (x_train, _), (x_test, _) = tf.keras.datasets.mnist.load_data()
    x = np.concatenate([x_train, x_test])  # 70 000 total

    n = min(args.n_samples, len(x))
    print(f"Writing {n} images at {args.image_size}×{args.image_size} → {args.out_dir}/")

    for i in range(n):
        gray = x[i]                                         # (28, 28) uint8
        rgb = np.stack([gray, gray, gray], axis=-1)         # (28, 28, 3)
        pil = Image.fromarray(rgb).resize(
            (args.image_size, args.image_size), Image.LANCZOS
        )
        pil.save(os.path.join(args.out_dir, f"mnist_{i:06d}.png"))

        if (i + 1) % 1000 == 0:
            print(f"  …{i + 1}/{n}")

    print(f"\nDone. {n} PNGs in {args.out_dir}/")


if __name__ == "__main__":
    main()
