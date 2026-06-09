"""
HiDDeN Encoder — strict paper + proposal implementation.

Per Zhu et al. 2018 §3 and our project proposal §4.1:

  cover image (B, H, W, 3)  ─►  Conv-BN-ReLU stack  ─►  image features
  message bits (B, L)       ─►  Dense projection    ─►  multi-channel message tensor (B, M)
                                                          │
                            spatial replication to (B, H, W, M)
                                                          │
                Concat(cover ⊕ image_features ⊕ msg_volume) along channel axis
                                                          │
                          1×1 Conv fuse to N channels
                                                          │
                          ResidualBlock × N (proposal §4.1: high-freq preservation)
                                                          │
                          Final 3×3 Conv → 3 channels, sigmoid
                                                          │
                                 Stego image I_en in [0, 1]    (direct, not residual)

Notes vs prior version:
  * The message is now passed through a Dense layer before spatial replication
    — matches the proposal verbatim:
      "The message is first projected through a dense layer and then
       transformed into a multi-channel feature tensor in order to address
       this. Before being concatenated channel-wise, this enlarged message
       is spatially replicated to match the dimensions of the image features."
  * The encoder now outputs the stego image directly — matches the paper:
      "After more convolutional layers, the encoder produces I_en, the
       encoded image."
    (Previous version was `cover + α·delta` for training stability; we keep
    sigmoid at the head so the output stays bounded in [0, 1].)
"""
from __future__ import annotations

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------
class ConvBNReLU(layers.Layer):
    """3×3 conv → BN → ReLU."""

    def __init__(self, channels: int, kernel: int = 3, **kw):
        super().__init__(**kw)
        self.conv = layers.Conv2D(channels, kernel, padding="same", use_bias=False)
        self.bn = layers.BatchNormalization()
        self.act = layers.ReLU()

    def call(self, x, training=False):
        return self.act(self.bn(self.conv(x), training=training))


class ResidualBlock(layers.Layer):
    """Standard residual block: x + Conv(BN(Conv(BN(x))))."""

    def __init__(self, channels: int, **kw):
        super().__init__(**kw)
        self.conv1 = ConvBNReLU(channels)
        self.conv2 = layers.Conv2D(channels, 3, padding="same", use_bias=False)
        self.bn2 = layers.BatchNormalization()

    def call(self, x, training=False):
        h = self.conv1(x, training=training)
        h = self.bn2(self.conv2(h), training=training)
        return tf.nn.relu(x + h)


# ---------------------------------------------------------------------------
# Encoder
# ---------------------------------------------------------------------------
class Encoder(keras.Model):
    """
    Inputs:
        cover   — (B, H, W, 3), float in [0, 1]
        message — (B, L),       binary bits (0.0 / 1.0)

    Output:
        stego   — (B, H, W, 3), float in [0, 1], visually similar to cover
    """

    def __init__(
        self,
        message_length: int = 32,
        message_projection_dim: int = 64,
        conv_channels: int = 64,
        num_residual_blocks: int = 4,
    ):
        super().__init__()
        self.L = message_length
        self.M = message_projection_dim

        # --- image feature extraction ---
        self.image_conv = ConvBNReLU(conv_channels)

        # --- message projection (proposal §4.1) ---
        # Dense → ReLU → reshape to a multi-channel tensor for spatial replication.
        self.message_dense = layers.Dense(self.M, activation="relu")

        # --- fuse cover + image_features + msg_volume to N channels ---
        self.fuse = layers.Conv2D(conv_channels, 1, padding="same", activation="relu")

        # --- residual stack (proposal §4.1) ---
        self.residual_blocks = [
            ResidualBlock(conv_channels) for _ in range(num_residual_blocks)
        ]

        # --- direct stego output (paper §3) ---
        # sigmoid keeps it bounded in [0, 1]; matches cover image range.
        self.out_conv = layers.Conv2D(3, 3, padding="same", activation="sigmoid")

    def call(self, inputs, training=False):
        cover, message = inputs

        B = tf.shape(cover)[0]
        H = tf.shape(cover)[1]
        W = tf.shape(cover)[2]

        # 1) image features
        img_feats = self.image_conv(cover, training=training)

        # 2) message → dense → multi-channel volume
        msg_feats = self.message_dense(message)            # (B, M)
        msg_feats = tf.reshape(msg_feats, (B, 1, 1, self.M))
        msg_vol = tf.tile(msg_feats, (1, H, W, 1))         # (B, H, W, M)

        # 3) concat (cover + image features + message volume)
        x = tf.concat([cover, img_feats, msg_vol], axis=-1)

        # 4) fuse to conv_channels
        x = self.fuse(x)

        # 5) residual stack
        for block in self.residual_blocks:
            x = block(x, training=training)

        # 6) direct stego output
        stego = self.out_conv(x)
        return stego
