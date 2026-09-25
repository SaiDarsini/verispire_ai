"""
Centralized application configuration for VeriSpire AI.
All environment-driven values live here so the rest of the app
never touches os.environ directly.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


CONFIG_FILE = Path(__file__).resolve()
BACKEND_DIR = CONFIG_FILE.parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILES = (BACKEND_DIR / ".env", PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    # App
    APP_NAME: str = "VeriSpire AI"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Security
    SECRET_KEY: str = "verispire-hackfusion-key-2026-secret"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database — SQLite by default so the app boots without Postgres.
    DATABASE_URL: str = "sqlite:///./verispire.db"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000"

    # Uploads
    UPLOAD_DIR: str = "app/uploads"
    MAX_UPLOAD_MB: int = 15

    # Email (optional)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "no-reply@verispire.ai"

    # AI Provider Settings — empty key is valid; the engine degrades gracefully.
    AI_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GOOGLE_API_KEY: str = ""
    BACKEND_URL: str = "http://localhost:8000"

    # Verifier engine
    VERIFIER_MAX_RETRIES: int = 2
    SANDBOX_TIMEOUT_SECONDS: float = 5.0

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fallback_sqlite(cls, value):
        if value is None:
            return "sqlite:///./verispire.db"
        text = str(value).strip()
        if not text or text.lower() in {"none", "null", "undefined"}:
            return "sqlite:///./verispire.db"
        return text

    @field_validator("GEMINI_API_KEY", mode="before")
    @classmethod
    def coerce_gemini_key(cls, value):
        if value is None:
            return ""
        return str(value).strip()

    @field_validator("SMTP_PORT", mode="before")
    @classmethod
    def coerce_smtp_port(cls, value):
        if value is None or value == "":
            return 587
        return value

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except Exception:
        # Last-resort defaults so a malformed .env never crashes import-time validation.
        return Settings(
            DATABASE_URL="sqlite:///./verispire.db",
            GEMINI_API_KEY="",
        )


settings = get_settings()
