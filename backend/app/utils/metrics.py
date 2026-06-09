"""Metrics calculation utilities"""
import numpy as np
from skimage.metrics import peak_signal_noise_ratio, structural_similarity


class MetricsCalculator:
    """Calculate quality metrics"""
    
    @staticmethod
    def calculate_psnr(original: np.ndarray, distorted: np.ndarray) -> float:
        """
        Calculate Peak Signal-to-Noise Ratio (PSNR)
        Higher is better (>40 dB is good for imperceptibility)
        """
        # Ensure values are in [0, 1]
        if original.max() > 1:
            original = original / 255.0
        if distorted.max() > 1:
            distorted = distorted / 255.0
        
        mse = np.mean((original - distorted) ** 2)
        
        if mse == 0:
            return 100.0  # Identical images
        
        psnr = 20 * np.log10(1.0 / np.sqrt(mse))
        return float(psnr)
    
    @staticmethod
    def calculate_ssim(original: np.ndarray, distorted: np.ndarray) -> float:
        """
        Calculate Structural Similarity Index (SSIM)
        Range: [-1, 1], 1 = identical
        >0.98 is good for imperceptibility
        """
        # Ensure values are in [0, 1] floats
        original = original.astype(np.float32)
        distorted = distorted.astype(np.float32)
        if original.max() > 1:
            original = original / 255.0
        if distorted.max() > 1:
            distorted = distorted / 255.0

        # Convert to grayscale if color
        if original.ndim == 3:
            original = np.mean(original, axis=2)
        if distorted.ndim == 3:
            distorted = np.mean(distorted, axis=2)

        # data_range is REQUIRED in skimage >= 0.21 for float images.
        ssim = structural_similarity(original, distorted, data_range=1.0)
        return float(ssim)
    
    @staticmethod
    def calculate_mse(original: np.ndarray, distorted: np.ndarray) -> float:
        """Calculate Mean Squared Error"""
        if original.max() > 1:
            original = original / 255.0
        if distorted.max() > 1:
            distorted = distorted / 255.0
        
        mse = np.mean((original - distorted) ** 2)
        return float(mse)
    
    @staticmethod
    def calculate_mae(original: np.ndarray, distorted: np.ndarray) -> float:
        """Calculate Mean Absolute Error"""
        if original.max() > 1:
            original = original / 255.0
        if distorted.max() > 1:
            distorted = distorted / 255.0
        
        mae = np.mean(np.abs(original - distorted))
        return float(mae)
    
    @staticmethod
    def calculate_bit_accuracy(original_bits: np.ndarray, decoded_bits: np.ndarray) -> float:
        """
        Calculate bit accuracy for message recovery
        Returns percentage of correctly recovered bits
        """
        if len(original_bits) != len(decoded_bits):
            raise ValueError("Bit arrays must have same length")
        
        # Round decoded bits to [0, 1]
        decoded_binary = (decoded_bits > 0.5).astype(int)
        
        accuracy = np.mean(original_bits == decoded_binary)
        return float(accuracy * 100)
    
    @staticmethod
    def calculate_ber(original_bits: np.ndarray, decoded_bits: np.ndarray) -> float:
        """
        Calculate Bit Error Rate (BER)
        Lower is better
        """
        accuracy = MetricsCalculator.calculate_bit_accuracy(original_bits, decoded_bits)
        return 100.0 - accuracy
    
    @staticmethod
    def calculate_robustness_score(
        psnr: float,
        ssim: float,
        bit_accuracy: float,
        weights: dict = None
    ) -> float:
        """
        Calculate overall robustness score
        Combines PSNR, SSIM, and bit accuracy
        """
        if weights is None:
            weights = {'psnr': 0.3, 'ssim': 0.3, 'accuracy': 0.4}
        
        # Normalize metrics to [0, 100]
        psnr_score = min(psnr / 50 * 100, 100)  # PSNR > 50 is excellent
        ssim_score = ssim * 100  # SSIM already in [0, 1]
        accuracy_score = bit_accuracy
        
        score = (
            weights['psnr'] * psnr_score +
            weights['ssim'] * ssim_score +
            weights['accuracy'] * accuracy_score
        )
        
        return float(score)
