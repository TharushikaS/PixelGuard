"""Image processing utilities"""
import cv2
import numpy as np
from PIL import Image
import io


class ImageProcessor:
    """Image processing utilities"""
    
    @staticmethod
    def load_image(image_path: str, size: int = 256) -> np.ndarray:
        """Load and preprocess image"""
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Convert BGR to RGB
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize to target size
        image = cv2.resize(image, (size, size))
        
        # Normalize to [0, 1]
        image = image.astype(np.float32) / 255.0
        
        return image
    
    @staticmethod
    def load_image_from_bytes(image_bytes: bytes, size: int | None = 256) -> np.ndarray:
        """
        Load image from bytes. If `size` is None, keep the original resolution
        (used by the LSB path so the stego image is bit-identical to the
        cover except for the LSBs).
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            raise ValueError("Could not decode image from bytes")

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        if size is not None:
            image = cv2.resize(image, (size, size))
        image = image.astype(np.float32) / 255.0

        return image
    
    @staticmethod
    def save_image(image: np.ndarray, output_path: str) -> None:
        """
        Save an RGB image to disk.

        Accepts either uint8 [0,255] or float [0,1]. Float input is
        rounded (not truncated) before casting to uint8, which is what
        keeps LSB-embedded watermarks intact across the float roundtrip.
        """
        if image.dtype != np.uint8:
            image = np.round(np.clip(image * 255.0, 0, 255)).astype(np.uint8)
        image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(output_path, image)
    
    @staticmethod
    def image_to_bytes(image: np.ndarray, format: str = 'png') -> bytes:
        """Convert image to bytes"""
        image = (image * 255).astype(np.uint8)
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        pil_image = Image.fromarray(image_rgb)
        
        buf = io.BytesIO()
        pil_image.save(buf, format=format.upper())
        buf.seek(0)
        
        return buf.getvalue()
    
    @staticmethod
    def convert_to_ycbcr(image: np.ndarray) -> np.ndarray:
        """Convert RGB image to YCbCr"""
        return cv2.cvtColor(image, cv2.COLOR_RGB2YCrCb)
    
    @staticmethod
    def convert_to_rgb(image: np.ndarray) -> np.ndarray:
        """Convert YCbCr image to RGB"""
        return cv2.cvtColor(image, cv2.COLOR_YCrCb2RGB)
    
    @staticmethod
    def add_padding(image: np.ndarray, size: int = 256) -> np.ndarray:
        """Add padding to image to reach target size"""
        h, w, c = image.shape
        
        if h >= size and w >= size:
            return cv2.resize(image, (size, size))
        
        # Create white background
        padded = np.ones((size, size, c), dtype=image.dtype) * 255
        
        # Center image on background
        y_offset = (size - h) // 2
        x_offset = (size - w) // 2
        
        padded[y_offset:y_offset+h, x_offset:x_offset+w] = image
        
        return padded
    
    @staticmethod
    def get_image_hash(image: np.ndarray) -> str:
        """Generate hash of image for uniqueness check"""
        import hashlib
        image_bytes = image.tobytes()
        return hashlib.sha256(image_bytes).hexdigest()
