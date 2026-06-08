"""
Noise Layer - Simulates real-world image distortions during training
Makes encoder/decoder robust to JPEG, cropping, resizing, blur, etc.
"""
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
import numpy as np


class NoiseLayer(keras.Model):
    """
    Differentiable Noise Layer
    Applies various image distortions during training to force robustness
    
    Distortions:
    - Spatial: Crop, Resize, Dropout
    - Frequency: JPEG approximation, Gaussian blur
    """
    
    def __init__(self, noise_type='identity', intensity=0.5):
        super(NoiseLayer, self).__init__()
        self.noise_type = noise_type
        self.intensity = intensity
    
    def call(self, image, training=False):
        """Apply noise transformation"""
        if not training:
            return image
        
        if self.noise_type == 'identity':
            return image
        elif self.noise_type == 'crop':
            return self._apply_crop(image)
        elif self.noise_type == 'resize':
            return self._apply_resize(image)
        elif self.noise_type == 'gaussian_blur':
            return self._apply_gaussian_blur(image)
        elif self.noise_type == 'dropout':
            return self._apply_dropout(image)
        elif self.noise_type == 'jpeg':
            return self._apply_jpeg_approximation(image)
        else:
            return image
    
    def _apply_crop(self, image):
        """Random cropping"""
        batch_size = tf.shape(image)[0]
        height = tf.shape(image)[1]
        width = tf.shape(image)[2]
        
        # Crop to p% of original size
        p = self.intensity  # 0.0 to 1.0
        crop_h = tf.cast(tf.cast(height, tf.float32) * p, tf.int32)
        crop_w = tf.cast(tf.cast(width, tf.float32) * p, tf.int32)
        
        # Ensure minimum crop size
        crop_h = tf.maximum(crop_h, 32)
        crop_w = tf.maximum(crop_w, 32)
        
        max_offset_h = height - crop_h
        max_offset_w = width - crop_w
        
        offset_h = tf.random.uniform([], 0, max_offset_h + 1, dtype=tf.int32)
        offset_w = tf.random.uniform([], 0, max_offset_w + 1, dtype=tf.int32)
        
        cropped = tf.image.crop_to_bounding_box(
            image, offset_h, offset_w, crop_h, crop_w
        )
        
        # Resize back to original size
        resized = tf.image.resize(cropped, (height, width))
        return resized
    
    def _apply_resize(self, image):
        """Random resizing"""
        height = tf.shape(image)[1]
        width = tf.shape(image)[2]
        
        # Resize to random scale
        scale = tf.random.uniform([], 0.7, 1.3)  # 70% to 130%
        new_height = tf.cast(tf.cast(height, tf.float32) * scale, tf.int32)
        new_width = tf.cast(tf.cast(width, tf.float32) * scale, tf.int32)
        
        resized = tf.image.resize(image, (new_height, new_width))
        
        # Pad or crop back to original size
        resized = tf.image.resize_with_crop_or_pad(resized, height, width)
        return resized
    
    def _apply_gaussian_blur(self, image):
        """Gaussian blur in frequency domain"""
        # Standard deviation for Gaussian kernel
        sigma = self.intensity * 5.0  # 0 to 5
        
        # Create Gaussian kernel
        kernel_size = 5
        x = tf.range(-kernel_size // 2 + 1., kernel_size // 2 + 1.)
        gauss_kernel = tf.exp(-tf.square(x) / (2 * tf.square(sigma)))
        gauss_kernel = gauss_kernel / tf.reduce_sum(gauss_kernel)
        
        # Apply convolution (build separable 2D kernel via outer product)
        kernel_2d = tf.tensordot(gauss_kernel, gauss_kernel, axes=0)
        kernel_2d = tf.expand_dims(tf.expand_dims(kernel_2d, -1), -1)
        kernel_2d = tf.tile(kernel_2d, [1, 1, tf.shape(image)[-1], 1])
        
        blurred = tf.nn.depthwise_conv2d(
            image, kernel_2d, strides=[1, 1, 1, 1], padding='SAME'
        )
        return blurred
    
    def _apply_dropout(self, image):
        """Pixel-wise dropout - replaces pixels with cover image"""
        drop_prob = self.intensity
        mask = tf.random.uniform(tf.shape(image)) > drop_prob
        mask = tf.cast(mask, tf.float32)
        
        # For this we'd need access to original cover image
        # Simplified: just apply mask to current image
        return image * mask
    
    def _apply_jpeg_approximation(self, image):
        """
        Differentiable JPEG approximation using DCT
        JPEG-Mask: Fixed masking of high-frequency coefficients
        """
        # Convert to 8x8 blocks
        batch_size = tf.shape(image)[0]
        height = tf.shape(image)[1]
        width = tf.shape(image)[2]
        channels = tf.shape(image)[3]
        
        # For simplicity, apply a rough approximation
        # Convert to YCbCr space (more like JPEG)
        image_ycbcr = tf.image.rgb_to_yuv(image)
        
        # Add quantization-like effect (rough approximation)
        quantization_factor = 1.0 / (1.0 + self.intensity)
        quantized = tf.round(image_ycbcr * 255.0 / quantization_factor) * quantization_factor / 255.0
        
        # Convert back to RGB
        image_rgb = tf.image.yuv_to_rgb(quantized)
        
        return image_rgb


class CombinedNoiseLayer(keras.Model):
    """
    Combined Noise Layer - Applies random distortions during training
    Randomly selects from multiple noise types for better generalization
    """
    
    def __init__(self):
        super(CombinedNoiseLayer, self).__init__()
        self.noise_layers = {
            'identity': NoiseLayer('identity'),
            'crop': NoiseLayer('crop', 0.8),
            'resize': NoiseLayer('resize'),
            'gaussian': NoiseLayer('gaussian_blur', 1.0),
            'dropout': NoiseLayer('dropout', 0.2),
            'jpeg': NoiseLayer('jpeg', 0.5),
        }
    
    def call(self, image, training=False):
        """Apply random noise distortion"""
        if not training:
            return image
        
        # Randomly select noise type
        noise_types = list(self.noise_layers.keys())
        random_idx = tf.random.uniform([], 0, len(noise_types), dtype=tf.int32)
        
        # Can't use tf.case with string keys, so we use a simpler approach
        # Randomly apply distortions
        prob = tf.random.uniform([])
        
        if prob < 0.2:
            return self.noise_layers['crop'](image, training)
        elif prob < 0.4:
            return self.noise_layers['resize'](image, training)
        elif prob < 0.6:
            return self.noise_layers['gaussian'](image, training)
        elif prob < 0.8:
            return self.noise_layers['jpeg'](image, training)
        else:
            return self.noise_layers['identity'](image, training)
