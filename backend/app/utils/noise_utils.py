"""Noise and distortion utilities"""
import numpy as np
import cv2


class NoiseProcessor:
    """Apply various noise/distortion effects"""
    
    @staticmethod
    def apply_jpeg_compression(image: np.ndarray, quality: int = 75) -> np.ndarray:
        """Apply JPEG compression"""
        # Encode to JPEG
        _, encoded = cv2.imencode('.jpg', (image * 255).astype(np.uint8), 
                                  [cv2.IMWRITE_JPEG_QUALITY, quality])
        
        # Decode back
        decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        
        # Convert back to float
        return decoded.astype(np.float32) / 255.0
    
    @staticmethod
    def apply_gaussian_blur(image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0) -> np.ndarray:
        """Apply Gaussian blur"""
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
    
    @staticmethod
    def apply_crop(image: np.ndarray, crop_percent: float = 0.8) -> np.ndarray:
        """Random crop and resize back"""
        h, w, c = image.shape
        
        crop_h = int(h * crop_percent)
        crop_w = int(w * crop_percent)
        
        y_start = np.random.randint(0, h - crop_h + 1)
        x_start = np.random.randint(0, w - crop_w + 1)
        
        cropped = image[y_start:y_start+crop_h, x_start:x_start+crop_w]
        
        # Resize back to original
        return cv2.resize(cropped, (w, h))
    
    @staticmethod
    def apply_resize(image: np.ndarray, scale_range: tuple = (0.7, 1.3)) -> np.ndarray:
        """Random resize"""
        h, w, c = image.shape
        scale = np.random.uniform(scale_range[0], scale_range[1])
        
        new_h = int(h * scale)
        new_w = int(w * scale)
        
        resized = cv2.resize(image, (new_w, new_h))
        
        # Pad or crop to original size
        if new_h < h or new_w < w:
            # Pad
            padded = np.zeros((h, w, c), dtype=image.dtype)
            y_offset = (h - new_h) // 2
            x_offset = (w - new_w) // 2
            padded[y_offset:y_offset+new_h, x_offset:x_offset+new_w] = resized
            return padded
        else:
            # Crop
            y_offset = (new_h - h) // 2
            x_offset = (new_w - w) // 2
            return resized[y_offset:y_offset+h, x_offset:x_offset+w]
    
    @staticmethod
    def apply_noise(image: np.ndarray, noise_type: str = 'gaussian', intensity: float = 0.01) -> np.ndarray:
        """Add various types of noise"""
        if noise_type == 'gaussian':
            noise = np.random.normal(0, intensity, image.shape)
            return np.clip(image + noise, 0, 1)
        
        elif noise_type == 'salt_pepper':
            s_vs_p = 0.5
            amount = intensity
            out = image.copy()
            
            # Salt
            num_salt = np.ceil(amount * image.size * s_vs_p)
            coords = [np.random.randint(0, i, int(num_salt)) for i in image.shape]
            out[tuple(coords)] = 1
            
            # Pepper
            num_pepper = np.ceil(amount * image.size * (1. - s_vs_p))
            coords = [np.random.randint(0, i, int(num_pepper)) for i in image.shape]
            out[tuple(coords)] = 0
            
            return out
        
        else:
            return image
    
    @staticmethod
    def apply_rotation(image: np.ndarray, angle: float) -> np.ndarray:
        """Apply rotation"""
        h, w = image.shape[:2]
        center = (w // 2, h // 2)
        
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(image, M, (w, h))
        
        return rotated
