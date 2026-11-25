"""
app/core/config.py
──────────────────
PURPOSE:
  Loads all configuration values from environment variables (.env file).
  This is the single source of truth for all settings.

WHY A SEPARATE CONFIG FILE?
  - Avoids hardcoding values like database URLs, secrets in source code.
  - Different environments (dev, test, production) use different .env files.
  - Pydantic Settings validates types automatically — if DATABASE_URL is missing,
    the app crashes on startup with a clear error (fail fast principle).

PATTERN: 12-Factor App configuration (industry standard)
"""

from pydantic_settings import BaseSettings
from typing import List
import json


class Settings(BaseSettings):
    # ── App Info ────────────────────────────────────────────────────────────────
    APP_NAME: str = "AI Testing Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── API ─────────────────────────────────────────────────────────────────────
    API_V1_PREFIX: str = "/api/v1"

    # ── CORS ────────────────────────────────────────────────────────────────────
    # List of frontend origins allowed to call this API
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:4200"]

    # ── Database ────────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+psycopg://postgres:password@localhost:5432/ai_testing_platform"

    # ── JWT Authentication ───────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-to-a-secure-random-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── File Storage ────────────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE_MB: int = 10
    ALLOWED_FILE_TYPES: List[str] = [
        "image/jpeg", "image/png", "image/gif",
        "application/pdf", "text/plain"
    ]

    # ── Super Admin Seed ────────────────────────────────────────────────────────
    FIRST_SUPERADMIN_EMAIL: str = "admin@platform.com"
    FIRST_SUPERADMIN_PASSWORD: str = "Admin@1234"
    FIRST_SUPERADMIN_NAME: str = "Platform Admin"

    class Config:
        # Tells Pydantic to look for a .env file and load values from it
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# Single instance reused throughout the entire application
# This follows the Singleton pattern
settings = Settings()
