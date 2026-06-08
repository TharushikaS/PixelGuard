"""
Configuration management for PixelGuard backend.

All settings can be overridden via environment variables or a `.env` file.
"""
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ---------- Application ----------
    APP_NAME: str = "PixelGuard"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # ---------- MongoDB ----------
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "pixelguard"
    MONGODB_TRACKING_COLLECTION: str = "tracking_ids"
    MONGODB_ENCODED_COLLECTION: str = "encoded_images"
    MONGODB_DECODE_LOG_COLLECTION: str = "decoding_logs"
    MONGODB_USERS_COLLECTION: str = "users"

    # ---------- Security ----------
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24h

    # ---------- CORS ----------
    # Accept comma-separated string in env, expose as list.
    ALLOWED_ORIGINS: List[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ]
    )

    # ---------- File upload ----------
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: List[str] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "bmp", "webp"]
    )

    # ---------- Model ----------
    MODEL_PATH: str = "./models"
    MESSAGE_LENGTH: int = 32          # tracking-ID bit length
    IMAGE_SIZE: int = 256             # input H = W
    INFERENCE_TIMEOUT: int = 30
    BATCH_SIZE: int = 1

    # ---------- Email (optional) ----------
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
