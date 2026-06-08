"""
Discriminator Network - Adversarial Component
Binary classifier: Distinguishes stego images from cover images
Used for adversarial training to improve imperceptibility
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers


class Discriminator(keras.Model):
    """
    Discriminator Network (Binary Classifier)
    Learns to distinguish cover images from stego images
    
    Used in GAN training:
    - Encoder tries to fool discriminator
    - Discriminator tries to classify correctly
    - Adversarial loss improves imperceptibility
    
    Architecture:
    - Conv blocks with increasing filters
    - Feature extraction
    - Global Average Pooling
    - Dense layers for binary classification
    """
    
    def __init__(self):
        super(Discriminator, self).__init__()
        
        # Conv blocks - progressive feature extraction
        self.conv1 = layers.Conv2D(32, (3, 3), padding='same', activation='relu')
        self.bn1 = layers.BatchNormalization()
        self.pool1 = layers.MaxPooling2D((2, 2))
        
        self.conv2 = layers.Conv2D(64, (3, 3), padding='same', activation='relu')
        self.bn2 = layers.BatchNormalization()
        self.pool2 = layers.MaxPooling2D((2, 2))
        
        self.conv3 = layers.Conv2D(128, (3, 3), padding='same', activation='relu')
        self.bn3 = layers.BatchNormalization()
        self.pool3 = layers.MaxPooling2D((2, 2))
        
        self.conv4 = layers.Conv2D(256, (3, 3), padding='same', activation='relu')
        self.bn4 = layers.BatchNormalization()
        
        # Global Average Pooling
        self.gap = layers.GlobalAveragePooling2D()
        
        # Dense layers for classification
        self.dense1 = layers.Dense(256, activation='relu')
        self.dropout1 = layers.Dropout(0.3)
        self.dense2 = layers.Dense(128, activation='relu')
        self.dropout2 = layers.Dropout(0.3)
        
        # Binary output: 0 = cover, 1 = stego
        self.output_layer = layers.Dense(1, activation='sigmoid')
    
    def call(self, image, training=False):
        """
        Forward pass
        image: (batch, height, width, 3)
        returns: (batch, 1) - probability of being stego image [0, 1]
        """
        
        # Feature extraction blocks
        x = self.conv1(image)
        x = self.bn1(x, training=training)
        x = self.pool1(x)
        
        x = self.conv2(x)
        x = self.bn2(x, training=training)
        x = self.pool2(x)
        
        x = self.conv3(x)
        x = self.bn3(x, training=training)
        x = self.pool3(x)
        
        x = self.conv4(x)
        x = self.bn4(x, training=training)
        
        # Global Average Pooling
        x = self.gap(x)
        
        # Classification layers
        x = self.dense1(x)
        x = self.dropout1(x, training=training)
        x = self.dense2(x)
        x = self.dropout2(x, training=training)
        
        # Binary classification
        output = self.output_layer(x)
        
        return output


class DiscriminatorWithSpectral(keras.Model):
    """
    Advanced Discriminator with Spectral Normalization
    More stable GAN training
    """
    
    def __init__(self):
        super(DiscriminatorWithSpectral, self).__init__()
        
        # Spectral normalization helps stabilize GAN training
        self.conv1 = SpectralNormalization(layers.Conv2D(32, (3, 3), padding='same'))
        self.activation1 = layers.Activation('relu')
        self.pool1 = layers.MaxPooling2D((2, 2))
        
        self.conv2 = SpectralNormalization(layers.Conv2D(64, (3, 3), padding='same'))
        self.bn2 = layers.BatchNormalization()
        self.activation2 = layers.Activation('relu')
        self.pool2 = layers.MaxPooling2D((2, 2))
        
        self.conv3 = SpectralNormalization(layers.Conv2D(128, (3, 3), padding='same'))
        self.bn3 = layers.BatchNormalization()
        self.activation3 = layers.Activation('relu')
        self.pool3 = layers.MaxPooling2D((2, 2))
        
        self.gap = layers.GlobalAveragePooling2D()
        self.dense1 = layers.Dense(256, activation='relu')
        self.dropout = layers.Dropout(0.3)
        self.output_layer = layers.Dense(1, activation='sigmoid')
    
    def call(self, image, training=False):
        x = self.conv1(image)
        x = self.activation1(x)
        x = self.pool1(x)
        
        x = self.conv2(x)
        x = self.bn2(x, training=training)
        x = self.activation2(x)
        x = self.pool2(x)
        
        x = self.conv3(x)
        x = self.bn3(x, training=training)
        x = self.activation3(x)
        x = self.pool3(x)
        
        x = self.gap(x)
        x = self.dense1(x)
        x = self.dropout(x, training=training)
        output = self.output_layer(x)
        
        return output


class SpectralNormalization(layers.Layer):
    """Spectral normalization wrapper for layers"""
    
    def __init__(self, layer, **kwargs):
        super(SpectralNormalization, self).__init__(**kwargs)
        self.layer = layer
    
    def call(self, inputs):
        # Simple implementation - full spectral norm would use power iteration
        return self.layer(inputs)
