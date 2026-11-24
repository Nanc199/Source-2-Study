"""
Source2Study - Configuration Module
Loads settings from .env file using pydantic-settings.
"""

import os
import shutil
import secrets
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


def _detect_tesseract_cmd() -> str:
    """Auto-detect Tesseract executable path on system."""
    env_path = os.getenv("TESSERACT_CMD", "")
    if env_path and os.path.isfile(env_path):
        return env_path
    
    candidates = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        shutil.which("tesseract") or "",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return ""


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    APP_NAME: str = "Source2Study"
    DATABASE_URL: str = "sqlite:///./studymind.db"
    SECRET_KEY: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    RESET_TOKEN_EXPIRE_HOURS: int = Field(
    default=1,
    validation_alias="RESET_PASSWORD_TOKEN_EXPIRE_HOURS"
)

    # Google Gemini API Key
    GEMINI_API_KEY: str = ""
    # High-speed primary model (2-3s response) with ultra-reliable fallback (<10s)
    GEMINI_MODEL: str = "gemini-3-flash-preview"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.1-flash-lite"

    # OCR Settings
    TESSERACT_CMD: str = Field(default_factory=_detect_tesseract_cmd)

    # Email / SMTP Settings
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = "kaur07nnancy@gmail.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "kaur07nnancy@gmail.com"
    SMTP_FROM_NAME: str = "Source2Study"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_ALLOW_DEV_FALLBACK: bool = False
    FRONTEND_URL: str = "http://localhost:3000"

    # Storage and processing
    UPLOAD_DIR: str = "./uploads"
    CHROMA_DIR: str = "./chroma_db"

    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".pptx", ".jpg", ".jpeg", ".png"]

    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    SIMILARITY_THRESHOLD: float = 0.85

    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
