"""Steganography service - core encoding/decoding logic"""
import numpy as np
import uuid
from typing import Tuple, Dict, Any
from app.models import Encoder, Decoder, Discriminator
from app.utils import ImageProcessor, MetricsCalculator, NoiseProcessor
from app.config import settings


class SteganographyService:
    """Service for encoding/decoding images with steganography"""
    
    def __init__(self):
        self.encoder = Encoder(message_length=settings.MESSAGE_LENGTH)
        self.decoder = Decoder(message_length=settings.MESSAGE_LENGTH)
        self.discriminator = Discriminator()
        
        # Try to load pretrained models
        self._load_models()
    
    def _load_models(self):
        """Load pretrained models if available. Fails silently in dev."""
        import os
        encoder_path = os.path.join(settings.MODEL_PATH, "encoder")
        decoder_path = os.path.join(settings.MODEL_PATH, "decoder")
        try:
            if os.path.exists(encoder_path + ".index") or os.path.exists(encoder_path):
                self.encoder.load_weights(encoder_path)
            if os.path.exists(decoder_path + ".index") or os.path.exists(decoder_path):
                self.decoder.load_weights(decoder_path)
            print("[stego] pretrained weights loaded (if present)")
        except Exception as exc:  # noqa: BLE001
            print(f"[stego] no pretrained weights ({exc}); using random init")
    
    def generate_tracking_id(self) -> str:
        """Generate a unique tracking ID"""
        return str(uuid.uuid4())[:16]  # 128-bit UUID truncated
    
    def message_to_binary(self, message: str) -> np.ndarray:
        """
        Convert message string to binary array
        Truncated to MESSAGE_LENGTH bits
        """
        # Convert string to bytes
        message_bytes = message.encode('utf-8')
        
        # Convert to binary
        binary_str = ''.join(format(byte, '08b') for byte in message_bytes)
        
        # Truncate/pad to MESSAGE_LENGTH
        if len(binary_str) < settings.MESSAGE_LENGTH:
            binary_str = binary_str + '0' * (settings.MESSAGE_LENGTH - len(binary_str))
        else:
            binary_str = binary_str[:settings.MESSAGE_LENGTH]
        
        # Convert to array
        binary_array = np.array([int(b) for b in binary_str], dtype=np.float32)
        
        return binary_array
    
    def binary_to_message(self, binary_array: np.ndarray) -> str:
        """Convert binary array back to message"""
        # Round to 0/1
        binary_ints = (binary_array > 0.5).astype(int)
        
        # Convert to string
        binary_str = ''.join(str(b) for b in binary_ints)
        
        # Split into bytes
        message_bytes = bytes(int(binary_str[i:i+8], 2) for i in range(0, len(binary_str), 8))
        
        # Decode to string (ignore errors)
        message = message_bytes.decode('utf-8', errors='ignore')
        
        return message.rstrip('\x00')
    
    def encode(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Encode tracking ID into cover image
        
        Args:
            cover_image: Original image (H x W x 3) in [0, 1]
            tracking_id: Message to encode
        
        Returns:
            encoded_image: Stego image (H x W x 3)
            metrics: PSNR, SSIM, etc.
        """
        # Convert message to binary
        message_binary = self.message_to_binary(tracking_id)
        
        # Add batch dimension
        cover_batch = np.expand_dims(cover_image, 0)  # (1, H, W, 3)
        message_batch = np.expand_dims(message_binary, 0)  # (1, MESSAGE_LENGTH)
        
        # Encode
        encoded_batch = self.encoder([cover_batch, message_batch], training=False)
        encoded_image = np.squeeze(encoded_batch, 0)
        
        # Ensure output is valid
        encoded_image = np.clip(encoded_image, 0, 1)
        
        # Calculate metrics
        psnr = MetricsCalculator.calculate_psnr(cover_image, encoded_image)
        ssim = MetricsCalculator.calculate_ssim(cover_image, encoded_image)
        
        metrics = {
            'tracking_id': tracking_id,
            'psnr': round(psnr, 2),
            'ssim': round(ssim, 4),
            'mse': round(MetricsCalculator.calculate_mse(cover_image, encoded_image), 6),
            'mae': round(MetricsCalculator.calculate_mae(cover_image, encoded_image), 6),
        }
        
        return encoded_image, metrics
    
    def decode(
        self,
        encoded_image: np.ndarray,
        apply_noise: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Decode tracking ID from (possibly distorted) image
        
        Args:
            encoded_image: Stego image (H x W x 3)
            apply_noise: Optional noise type to apply before decoding
        
        Returns:
            tracking_id: Recovered message
            metrics: Confidence, etc.
        """
        # Apply noise if specified
        if apply_noise:
            processor = NoiseProcessor()
            if apply_noise == 'jpeg':
                encoded_image = processor.apply_jpeg_compression(encoded_image, quality=75)
            elif apply_noise == 'blur':
                encoded_image = processor.apply_gaussian_blur(encoded_image)
            elif apply_noise == 'crop':
                encoded_image = processor.apply_crop(encoded_image, 0.8)
            elif apply_noise == 'resize':
                encoded_image = processor.apply_resize(encoded_image)
        
        # Ensure image is in valid range
        encoded_image = np.clip(encoded_image, 0, 1)
        
        # Add batch dimension
        image_batch = np.expand_dims(encoded_image, 0)  # (1, H, W, 3)
        
        # Decode
        message_batch = self.decoder(image_batch, training=False)
        message_binary = np.squeeze(message_batch, 0)
        
        # Convert to tracking ID
        tracking_id = self.binary_to_message(message_binary)
        
        # Calculate confidence
        confidence = np.mean(np.abs(message_binary - 0.5)) * 2  # 0 to 1
        confidence = min(confidence * 100, 100)  # Convert to percentage
        
        metrics = {
            'tracking_id': tracking_id,
            'confidence': round(confidence, 2),
            'bit_accuracy': round(MetricsCalculator.calculate_bit_accuracy(
                np.round(message_binary), message_binary
            ), 2),
        }
        
        return tracking_id, metrics
    
    def test_robustness(
        self,
        cover_image: np.ndarray,
        tracking_id: str,
        distortions: list = None,
    ) -> Dict[str, Any]:
        """
        Test robustness of encoding against various distortions
        
        Args:
            cover_image: Original image
            tracking_id: Message to encode
            distortions: List of distortion types to test
        
        Returns:
            results: Accuracy and metrics for each distortion
        """
        if distortions is None:
            distortions = ['identity', 'jpeg', 'blur', 'crop', 'resize']
        
        # Encode
        encoded_image, encode_metrics = self.encode(cover_image, tracking_id)
        
        # Test each distortion
        results = {
            'tracking_id': tracking_id,
            'encode_metrics': encode_metrics,
            'robustness_tests': {}
        }
        
        for distortion in distortions:
            decoded_id, decode_metrics = self.decode(encoded_image, apply_noise=distortion)
            
            success = (decoded_id == tracking_id)
            results['robustness_tests'][distortion] = {
                'success': success,
                'decoded_id': decoded_id,
                'confidence': decode_metrics['confidence'],
            }
        
        return results
