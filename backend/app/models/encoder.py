"""
Encoder Network - FCN Architecture
Embeds tracking ID into cover image
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np


class Encoder(keras.Model):
    """
    Fully Convolutional Encoder Network
    Embeds a binary message into a cover image
    
    Architecture:
    - Conv blocks to extract image features
    - Message projection and spatial replication
    - Residual blocks for deep embedding
    - Output: Encoded image (stego image)
    """
    
    def __init__(self, message_length=32, image_channels=3):
        super(Encoder, self).__init__()
        self.message_length = message_length
        self.image_channels = image_channels
        
        # Initial conv blocks
        self.conv1 = layers.Conv2D(64, (3, 3), padding='same', activation='relu')
        self.bn1 = layers.BatchNormalization()
        
        self.conv2 = layers.Conv2D(128, (3, 3), padding='same', activation='relu')
        self.bn2 = layers.BatchNormalization()
        
        # Message processing
        self.message_dense = layers.Dense(256, activation='relu')
        self.message_projection = layers.Dense(16 * 16)  # Multi-channel tensor
        
        # 1x1 projection after image+message concatenation, so the residual
        # blocks see a consistent channel count.
        self.fuse_projection = layers.Conv2D(128, (1, 1), padding='same', activation='relu')

        # Residual blocks (4 blocks)
        self.residual_blocks = self._build_residual_blocks()

        # Output conv -- sigmoid keeps stego image in [0,1] like the cover
        self.output_conv = layers.Conv2D(
            image_channels, (3, 3), padding='same', activation='sigmoid'
        )
    
    def _build_residual_blocks(self, num_blocks=4):
        """Build residual blocks for deep feature learning"""
        blocks = []
        for _ in range(num_blocks):
            blocks.append(ResidualBlock(128))
        return blocks
    
    def call(self, inputs, training=False):
        """
        Forward pass
        inputs: (cover_image, message) tuple
            - cover_image: (batch, height, width, 3)
            - message: (batch, message_length) one-hot or binary
        """
        cover_image, message = inputs
        
        # Get spatial dimensions
        batch_size = tf.shape(cover_image)[0]
        height = tf.shape(cover_image)[1]
        width = tf.shape(cover_image)[2]
        
        # Extract image features
        x = self.conv1(cover_image)
        x = self.bn1(x, training=training)
        
        x = self.conv2(x)
        x = self.bn2(x, training=training)
        
        # Process message
        msg_feat = self.message_dense(message)  # (batch, 256)
        msg_feat = self.message_projection(msg_feat)  # (batch, 256)
        
        # Reshape message to multi-channel tensor
        msg_feat = tf.reshape(msg_feat, (batch_size, 16, 16, 1))
        
        # Resize message to match image spatial dimensions
        msg_feat = tf.image.resize(msg_feat, (height, width))
        
        # Tile to match feature channels
        msg_feat = tf.tile(msg_feat, (1, 1, 1, tf.shape(x)[-1]))
        
        # Concatenate message with image features and project back to 128 ch
        x = tf.concat([x, msg_feat], axis=-1)
        x = self.fuse_projection(x)

        # Residual blocks
        for block in self.residual_blocks:
            x = block(x, training=training)
        
        # Output encoding
        encoded = self.output_conv(x)
        
        # Ensure output is same shape as input
        encoded = tf.image.resize(encoded, (height, width))
        
        return encoded


class ResidualBlock(keras.Model):
    """Residual block for deep feature learning"""
    
    def __init__(self, filters=128):
        super(ResidualBlock, self).__init__()
        self.conv1 = layers.Conv2D(filters, (3, 3), padding='same', activation='relu')
        self.bn1 = layers.BatchNormalization()
        self.conv2 = layers.Conv2D(filters, (3, 3), padding='same')
        self.bn2 = layers.BatchNormalization()
        self.activation = layers.ReLU()
    
    def call(self, x, training=False):
        residual = x
        
        # Conv path
        out = self.conv1(x)
        out = self.bn1(out, training=training)
        out = self.conv2(out)
        out = self.bn2(out, training=training)
        
        # Add residual connection
        out = layers.Add()([out, residual])
        out = self.activation(out)
        
        return out
