"""
Adversarial Discriminator — paper-faithful HiDDeN architecture.

The discriminator's job is to classify an input image as either a
"cover" (clean original) or "stego" (one that has been encoded). The
encoder is trained to fool it: that adversarial pressure is what keeps
the stego image visually indistinguishable from the cover, beyond what
the plain L2 image-distortion loss alone could do.

Same conv→GAP shape as the decoder (Section 3 of Zhu et al. 2018), but
the head is a single scalar logit instead of an L-dim vector.

Returns LOGITS — use BCE-with-logits in the training loss.
"""
from __future__ import annotations

from tensorflow import keras
from tensorflow.keras import layers

from .encoder import ConvBNReLU


class Discriminator(keras.Model):
    def __init__(self, conv_channels: int = 64, num_conv_blocks: int = 3):
        super().__init__()

        self.conv_blocks = [
            ConvBNReLU(conv_channels) for _ in range(num_conv_blocks)
        ]
        self.gap = layers.GlobalAveragePooling2D()
        self.linear = layers.Dense(1)  # single logit

    def call(self, image, training=False):
        x = image
        for block in self.conv_blocks:
            x = block(x, training=training)
        x = self.gap(x)
        return self.linear(x)  # (B, 1) logit
