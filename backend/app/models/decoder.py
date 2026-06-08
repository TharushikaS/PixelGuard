"""
Decoder Network - GAP-Based Architecture
Recovers tracking ID from encoded (possibly distorted) image
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


class Decoder(keras.Model):
    """
    Global Average Pooling (GAP) Based Decoder
    Extracts binary message from encoded image
    
    Key Innovation: GAP makes decoder robust to cropping/resizing
    Statistical distribution of signal remains constant despite spatial changes
    
    Architecture:
    - Conv blocks to extract features
    - Global Average Pooling across spatial dimensions
    - Dense layers for message reconstruction
    - Output: Binary message (0 or 1)
    """
    
    def __init__(self, message_length=32):
        super(Decoder, self).__init__()
        self.message_length = message_length
        
        # Conv blocks for feature extraction
        self.conv1 = layers.Conv2D(64, (3, 3), padding='same', activation='relu')
        self.bn1 = layers.BatchNormalization()
        
        self.conv2 = layers.Conv2D(128, (3, 3), padding='same', activation='relu')
        self.bn2 = layers.BatchNormalization()
        
        self.conv3 = layers.Conv2D(256, (3, 3), padding='same', activation='relu')
        self.bn3 = layers.BatchNormalization()
        
        # Create L feature channels (where L = message_length)
        self.conv_msg = layers.Conv2D(message_length, (3, 3), padding='same')
        
        # Global Average Pooling
        self.gap = layers.GlobalAveragePooling2D()
        
        # Dense layers for message decoding
        self.dense1 = layers.Dense(128, activation='relu')
        self.dense2 = layers.Dense(64, activation='relu')
        self.dense3 = layers.Dense(message_length, activation='sigmoid')
        
        self.dropout = layers.Dropout(0.2)
    
    def call(self, encoded_image, training=False):
        """
        Forward pass
        encoded_image: (batch, height, width, 3) - possibly distorted
        returns: (batch, message_length) - predicted message bits
        """
        
        # Extract features from image
        x = self.conv1(encoded_image)
        x = self.bn1(x, training=training)
        x = layers.MaxPooling2D((2, 2))(x)
        
        x = self.conv2(x)
        x = self.bn2(x, training=training)
        x = layers.MaxPooling2D((2, 2))(x)
        
        x = self.conv3(x)
        x = self.bn3(x, training=training)
        
        # Create message-length feature channels
        x = self.conv_msg(x)  # (batch, H', W', message_length)
        
        # Global Average Pooling - KEY ROBUSTNESS MECHANISM
        # Collapses spatial dimensions (H', W') to vector
        # Statistical properties persist even after cropping/resizing
        x = self.gap(x)  # (batch, message_length)
        
        # Dense layers for message reconstruction
        x = self.dense1(x)
        x = self.dropout(x, training=training)
        x = self.dense2(x)
        x = self.dropout(x, training=training)
        
        # Output binary message
        message = self.dense3(x)  # (batch, message_length)
        
        return message


class DecoderWithLocalization(keras.Model):
    """
    Enhanced Decoder with optional localization network
    Can detect watermarked region before decoding (for robustness to large crops)
    """
    
    def __init__(self, message_length=32, use_localization=False):
        super(DecoderWithLocalization, self).__init__()
        self.message_length = message_length
        self.use_localization = use_localization
        
        if use_localization:
            # Localization network (semantic segmentation approach)
            self.localization_net = self._build_localization_net()
        
        # Standard decoder
        self.decoder = Decoder(message_length)
    
    def _build_localization_net(self):
        """Build localization network to find watermarked region"""
        inputs = keras.Input(shape=(None, None, 3))
        
        # Downsampling path
        x = layers.Conv2D(32, (3, 3), padding='same', activation='relu')(inputs)
        x = layers.MaxPooling2D((2, 2))(x)
        
        x = layers.Conv2D(64, (3, 3), padding='same', activation='relu')(x)
        x = layers.MaxPooling2D((2, 2))(x)
        
        # Upsampling path
        x = layers.Conv2DTranspose(32, (3, 3), strides=(2, 2), padding='same', activation='relu')(x)
        x = layers.Conv2DTranspose(16, (3, 3), strides=(2, 2), padding='same', activation='relu')(x)
        
        # Output mask
        outputs = layers.Conv2D(1, (1, 1), activation='sigmoid')(x)
        
        return keras.Model(inputs=inputs, outputs=outputs)
    
    def call(self, encoded_image, training=False):
        """Forward pass with optional localization"""
        
        if self.use_localization:
            # Detect watermarked region
            mask = self.localization_net(encoded_image, training=training)
            # Apply mask to encoded image
            encoded_image = encoded_image * mask
        
        # Decode message
        message = self.decoder(encoded_image, training=training)
        
        return message
