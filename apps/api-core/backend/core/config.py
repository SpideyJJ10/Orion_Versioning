"""
backend/core/config.py — Centralized configuration parsing with dev warnings.

Loads environment variables with sensible defaults for dev while raising
explicit warnings/errors if critical security configuration is missing.
"""
import os
import sys
import warnings

ENV = os.getenv("ENV", "dev").lower()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
APP_NAME = "Orion API"
APP_VERSION = "3.1.0"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tizon.db")

SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY or SECRET_KEY == "change-me-to-a-32+-char-random-string":
    if ENV in {"prod", "production"}:
        raise RuntimeError("SECRET_KEY seguro es obligatorio en producción.")
    warnings.warn(
        "⚠️  SECRET_KEY no configurado o inseguro. "
        "Configura SECRET_KEY en .env antes de desplegar.",
        stacklevel=2,
    )
    if not SECRET_KEY:
        SECRET_KEY = "dev-insecure-key-do-not-use-in-production-change-me"

ADMIN_PIN = os.getenv("ADMIN_PIN", "")
if not ADMIN_PIN or ADMIN_PIN == "1234":
    if ENV in {"prod", "production"}:
        raise RuntimeError("ADMIN_PIN seguro es obligatorio en producción.")
    warnings.warn(
        "⚠️  ADMIN_PIN no configurado o es '1234'. "
        "Cámbialo en .env antes de producción.",
        stacklevel=2,
    )
    if not ADMIN_PIN:
        ADMIN_PIN = "1234"

CORS_ORIGINS_STR = os.getenv("CORS_ORIGINS", "")
CORS_ORIGIN_REGEX = os.getenv("CORS_ORIGIN_REGEX", "").strip() or None


def cors_origins() -> list[str]:
    """Parse CORS_ORIGINS env into a list. Rejects wildcard in production."""
    if not CORS_ORIGINS_STR or CORS_ORIGINS_STR.strip() == "*":
        if ENV in {"prod", "production"}:
            raise RuntimeError("CORS_ORIGINS seguro es obligatorio en producción (no '*' ni vacío).")
        return ["*"]
    return [o.strip().rstrip("/") for o in CORS_ORIGINS_STR.split(",") if o.strip()]


def cors_origin_regex() -> str | None:
    """Optional regex for dynamic origins (e.g. Vercel preview deploys)."""
    return CORS_ORIGIN_REGEX
