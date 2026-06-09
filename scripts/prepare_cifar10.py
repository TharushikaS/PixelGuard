#!/usr/bin/env python3
"""
Prepare CIFAR-10 as PNG images for HiDDeN training.

CIFAR-10 is already 32×32 RGB photos — no resize or channel hack needed.
60 000 diverse images of cars, planes, animals, etc. Much better signal
for the encoder to learn texture-based embeddings than MNIST.

Usage:
    python scripts/prepare_cifar10.py --out-dir ./cifar_images --n-samples 20000
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import tensorflow as tf
from PIL import Image


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", default="./cifar_images")
    p.add_argument("--n-samples", type=int, default=20000,
                   help="How many CIFAR images to dump (max 60 000)")
    args = p.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    print("Downloading CIFAR-10 (cached in ~/.keras/ after first run)…")
    (x_train, _), (x_test, _) = tf.keras.datasets.cifar10.load_data()
    x = np.concatenate([x_train, x_test])  # 60 000, shape (N, 32, 32, 3) uint8

    n = min(args.n_samples, len(x))
    print(f"Writing {n} 32×32 RGB PNGs → {args.out_dir}/")

    for i in range(n):
        Image.fromarray(x[i]).save(os.path.join(args.out_dir, f"cifar_{i:06d}.png"))
        if (i + 1) % 2000 == 0:
            print(f"  …{i + 1}/{n}")

    print(f"\nDone. {n} PNGs in {args.out_dir}/")


if __name__ == "__main__":
    main()
