"""
HiDDeN Decoder — paper-faithful implementation.

Recipe (Section 3 of Zhu et al. 2018):

    stego (B, H, W, 3)
        │
        ├─► [ConvBNReLU(C)] × 7    (7 conv blocks at full resolution)
        │
        ├─► Conv2D(L, 3×3)         → (B, H, W, L) message channels
        │
        ├─► GlobalAveragePooling2D → (B, L)
        │
        └─► Dense(L)               → (B, L) logits

Two critical design choices straight from the paper:

  1. No spatial downsampling. We keep H×W throughout the conv stack so the
     channel-L message feature map at the end carries information from all
     pixel positions equally.
  2. GAP collapses spatial dims at the very end. This is what makes the
     decoder robust to crop/resize — the tracking ID is encoded as a
     global statistic, not at any particular pixel location.

Returns LOGITS (no sigmoid) so the caller can use BCE-with-logits during
training for numerical stability. At inference time, apply sigmoid.
"""
from __future__ import annotations

from tensorflow import keras
from tensorflow.keras import layers

from .encoder import ConvBNReLU


class Decoder(keras.Model):
    def __init__(
        self,
        message_length: int = 32,
        conv_channels: int = 64,
        num_conv_blocks: int = 7,
    ):
        super().__init__()
        self.L = message_length

        # Stack of conv blocks at full resolution.
        self.conv_blocks = [ConvBNReLU(conv_channels) for _ in range(num_conv_blocks)]

        # Project to L feature channels (one per message bit).
        self.to_msg_channels = layers.Conv2D(message_length, 3, padding="same")

        # Spatial collapse — the robustness trick.
        self.gap = layers.GlobalAveragePooling2D()

        # Final linear layer outputs LOGITS (no activation).
        self.linear = layers.Dense(message_length)

    def call(self, stego, training=False):
        x = stego
        for block in self.conv_blocks:
            x = block(x, training=training)

        x = self.to_msg_channels(x)   # (B, H, W, L)
        x = self.gap(x)                # (B, L)
        logits = self.linear(x)        # (B, L)
        return logits
