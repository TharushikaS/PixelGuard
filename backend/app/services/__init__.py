"""Services package."""
from .lsb_service import LSBSteganographyService
from .steganography_service import SteganographyService
from .tracking_service import TrackingService

__all__ = [
    "LSBSteganographyService",
    "SteganographyService",
    "TrackingService",
    "get_stego_service",
]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def get_stego_service():
    """
    Return the steganography backend selected by STEGO_METHOD env var.
    Default = "lsb" (works without training).
    Set STEGO_METHOD=neural once you've trained the TF models.
    """
    from app.config import settings  # late import to avoid cycle

    method = getattr(settings, "STEGO_METHOD", "lsb").lower()
    if method == "neural":
        return SteganographyService()
    return LSBSteganographyService()
