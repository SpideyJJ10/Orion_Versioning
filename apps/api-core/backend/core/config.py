"""
Configuración cargada desde el entorno (.env en la raíz del proyecto).
"""
from __future__ import annotations

import os
import secrets
import warnings
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Raíz del repo (directorio que contiene /backend y /frontend)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tizon.db")
ENV = os.getenv("ENV", "dev").lower()

# ── Security — fail loudly if defaults are used ──────────────────────────
SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY or SECRET_KEY.startswith("cambia"):
    if ENV in {"prod", "production"}:
        raise RuntimeError("SECRET_KEY es obligatorio en produccion.")
    SECRET_KEY = "dev_fallback_secret_key_for_orion_api_only"
    warnings.warn(
        "⚠️  SECRET_KEY no configurado. Se usó una clave estática para desarrollo. "
        "Configura SECRET_KEY en .env para producción.",
        stacklevel=2,
    )

ADMIN_PIN = os.getenv("ADMIN_PIN", "")
if not ADMIN_PIN or ADMIN_PIN == "1234":
    if ENV in {"prod", "production"}:
        raise RuntimeError("ADMIN_PIN seguro es obligatorio en produccion.")
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
    """Parse CORS_ORIGINS env into a list. Strict validation lives in
    `backend/core/security.py::strict_cors_origins` (used in production)."""
    if not CORS_ORIGINS_STR or CORS_ORIGINS_STR.strip() == "*":
        return ["*"]
    return [o.strip().rstrip("/") for o in CORS_ORIGINS_STR.split(",") if o.strip()]


def cors_origin_regex() -> str | None:
    """Optional regex for dynamic origins (e.g. Vercel preview deploys).

    Example: ``^https://orion-pos-.*\\.vercel\\.app$`` matches all preview
    deployments under the `orion-pos` Vercel project. The regex is anchored
    with ``^...$`` so partial matches are rejected.

    Returns ``None`` if `CORS_ORIGIN_REGEX` is not set.
    """
    return CORS_ORIGIN_REGEX
