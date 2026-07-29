"""
Inicialización opt-in de Sentry para el backend.

Si la variable `SENTRY_DSN` está definida y `sentry-sdk` está instalado, se
activa el SDK con la integración de FastAPI. En cualquier otro caso (dev local
sin DSN, dependencia ausente), `init_sentry()` es un no-op silencioso.

Uso desde `backend/main.py`:

    from backend.core.sentry import init_sentry
    init_sentry()  # llamar antes de crear la FastAPI app

Configuración por entorno:
    SENTRY_DSN              — DSN del proyecto (obligatorio para activar)
    SENTRY_ENVIRONMENT      — opcional, fallback a ENV o "dev"
    SENTRY_RELEASE          — opcional, normalmente el SHA del commit
    SENTRY_TRACES_SAMPLE_RATE   — float [0..1], default 0.1
    SENTRY_PROFILES_SAMPLE_RATE — float [0..1], default 0.0
"""
from __future__ import annotations

import os

from backend.core.logger import logger


def init_sentry() -> None:
    """Activa Sentry si hay DSN y SDK disponibles. No falla si faltan."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk  # type: ignore[import-not-found]
        from sentry_sdk.integrations.fastapi import FastApiIntegration  # type: ignore[import-not-found]
        from sentry_sdk.integrations.starlette import StarletteIntegration  # type: ignore[import-not-found]
    except ImportError:
        logger.warning(
            "SENTRY_DSN configurado pero `sentry-sdk` no está instalado. "
            "Añade `sentry-sdk[fastapi]` a requirements.txt."
        )
        return

    env = os.getenv("SENTRY_ENVIRONMENT") or os.getenv("ENV", "dev")
    release = os.getenv("SENTRY_RELEASE") or None

    try:
        traces = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1"))
    except ValueError:
        traces = 0.1
    try:
        profiles = float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.0"))
    except ValueError:
        profiles = 0.0

    sentry_sdk.init(
        dsn=dsn,
        environment=env,
        release=release,
        traces_sample_rate=traces,
        profiles_sample_rate=profiles,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
        ],
        # No PII por defecto; ajustar manualmente si se requiere.
        send_default_pii=False,
        # Suprime ruido de health checks y favicon.
        ignore_errors=[],
    )
    logger.info(f"Sentry inicializado · env={env} · traces={traces} · profiles={profiles}")
