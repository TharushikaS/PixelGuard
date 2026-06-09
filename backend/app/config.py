"""
Configuration management for PixelGuard backend.

All settings can be overridden via environment variables or a `.env` file.
Comma-separated env values are accepted for list fields (ALLOWED_ORIGINS,
ALLOWED_EXTENSIONS) — without `NoDecode`, pydantic-settings would try to
JSON-decode the raw env value first and crash on plain CSV.
"""
from typing import Annotated, List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_csv(value: object) -> object:
    """Accept either a list (already parsed), a JSON list, or CSV."""
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return []
        if s.startswith("[") and s.endswith("]"):
            import json
            return json.loads(s)
        return [item.strip() for item in s.split(",") if item.strip()]
    return value


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
    # `NoDecode` disables pydantic-settings' JSON parsing for this field
    # so our validator below can accept comma-separated values.
    ALLOWED_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
        ]
    )

    # ---------- File upload ----------
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50 MB
    UPLOAD_DIR: str = "./uploads"
    ALLOWED_EXTENSIONS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["jpg", "jpeg", "png", "bmp", "webp"]
    )

    # ---------- Model ----------
    # "lsb"    -> classical LSB (works without training; not noise-robust)
    # "neural" -> TensorFlow encoder/decoder (requires trained weights)
    STEGO_METHOD: str = "lsb"
    MODEL_PATH: str = "./models"
    MESSAGE_LENGTH: int = 32          # tracking-ID bit length (neural path)
    IMAGE_SIZE: int = 128             # input H = W (neural path); 128 matches paper
    INFERENCE_TIMEOUT: int = 30
    BATCH_SIZE: int = 1

    # ---------- Email (optional) ----------
    SMTP_SERVER: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None

    # ------------------------------------------------------------------
    # Now that NoDecode hands us the raw string, parse CSV ourselves.
    # ------------------------------------------------------------------
    @field_validator("ALLOWED_ORIGINS", "ALLOWED_EXTENSIONS", mode="before")
    @classmethod
    def _parse_csv_lists(cls, value: object) -> object:
        return _split_csv(value)

    # ------------------------------------------------------------------
    # Treat empty-string env values for optional fields as "unset".
    # Without this, `SMTP_PORT=` in .env breaks int parsing.
    # ------------------------------------------------------------------
    @field_validator(
        "SMTP_SERVER", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
        mode="before",
    )
    @classmethod
    def _empty_string_to_none(cls, value: object) -> object:
        if isinstance(value, str) and value.strip() == "":
            return None
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
