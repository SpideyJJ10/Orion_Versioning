"""
FastAPI entry point for Orion v3.

Responsibilities:
  - Wire CORS, security middleware, and routers.
  - Bootstrap DB schema (idempotent) and seed the first super-admin.
  - Backfill v3 rows (TenantBranding, Usuario, Sucursal) for legacy tenants.

The frontend is NOT served from this process anymore. Run the Next.js app at
`frontend-next/` (or `web/`) separately. See `docs/MASTER_GUIDE.md` §6.
"""
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend.auth_v3.passwords import hash_password
from backend.core.config import cors_origin_regex, cors_origins
from backend.core.logger import logger
from backend.core.security import init_security
from backend.core.sentry import init_sentry
from backend.db.session import Base, SessionLocal, engine
from backend.models import orm as _orm  # noqa: F401 — register models on metadata
from backend.models.orm import OnboardingProgress, Sucursal, Tenant, TenantBranding, Usuario
from backend.routes import (
    admin,
    auth_v3,
    branding,
    categorias,
    copilot,
    inventario,
    ml,
    onboarding,
    ordenes,
    productos,
    reportes,
    sucursales,
    usuarios,
    ventas,
    negocio,
    ai,
    payments,
    mesas,
    oai,
    copilot,
)


# ─────────────────────────────────────────────────────────────────────────
#  Bootstrap helpers
# ─────────────────────────────────────────────────────────────────────────
def _seed_admin() -> None:
    """Create the first super-admin if none exists, using ADMIN_EMAIL/ADMIN_PASSWORD env vars.

    Email is normalised to lowercase to match `auth_v3.login` lookup.
    """
    admin_email    = os.getenv("ADMIN_EMAIL", "").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not admin_email or not admin_password:
        return
    db = SessionLocal()
    try:
        exists = db.query(Tenant).filter(Tenant.es_admin == True).first()  # noqa: E712
        if exists:
            return
        admin_user = Tenant(
            email         = admin_email,
            password_hash = hash_password(admin_password),
            nombre        = "Super Admin",
            plan          = "admin",
            es_admin      = True,
            plan_activo   = True,
        )
        db.add(admin_user)
        db.commit()
        logger.info(f"Super-admin tenant created: {admin_email}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create super-admin: {e}")
    finally:
        db.close()


def _backfill_tenants_v3() -> None:
    """Idempotent migration: ensure every Tenant has a Branding, Onboarding row,
    a default Sucursal and a matching Usuario (owner / super_admin).

    Runs on every cold start. Only inserts missing rows.
    """
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        creados = 0
        for t in tenants:
            # 1) Default branding
            if not db.query(TenantBranding).filter_by(tenant_id=t.id).first():
                db.add(TenantBranding(
                    tenant_id        = t.id,
                    nombre_comercial = t.nombre or t.email.split("@")[0],
                    nicho            = "restaurante",
                ))
                creados += 1
            # 2) Onboarding tracking — admins are pre-marked as completed
            if not db.query(OnboardingProgress).filter_by(tenant_id=t.id).first():
                op = OnboardingProgress(tenant_id=t.id)
                if t.es_admin:
                    op.perfil_configurado = True
                    op.primer_producto    = True
                    op.primera_venta      = True
                    op.saltado            = True
                db.add(op)
            # 3) Default Sucursal "Principal" (skip for admin tenants)
            sucursal_default_id = None
            if not t.es_admin:
                sucursal_existente = db.query(Sucursal).filter_by(
                    tenant_id=t.id, activo=True
                ).first()
                if sucursal_existente:
                    sucursal_default_id = sucursal_existente.id
                else:
                    s = Sucursal(tenant_id=t.id, nombre="Principal")
                    db.add(s)
                    db.flush()
                    sucursal_default_id = s.id
            # 4) Owner / super-admin Usuario
            rol_default = "super_admin" if t.es_admin else "owner"
            existente = db.query(Usuario).filter_by(tenant_id=t.id, email=t.email).first()
            if not existente:
                db.add(Usuario(
                    tenant_id     = t.id,
                    email         = t.email,
                    password_hash = t.password_hash,
                    nombre        = t.nombre or "Propietario",
                    rol           = rol_default,
                    sucursal_id   = sucursal_default_id,
                    activo        = True,
                ))
            elif not existente.sucursal_id and sucursal_default_id:
                existente.sucursal_id = sucursal_default_id
        db.commit()
        if creados:
            logger.info(f"v3 backfill: created branding/onboarding rows for {creados} tenants")
    except Exception as e:
        db.rollback()
        logger.error(f"v3 backfill failed: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables (SQLite) or verify schema (Postgres + alembic) at startup."""
    logger.info("Starting Orion API")
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema verified/created")
        _seed_admin()
        _backfill_tenants_v3()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    logger.info("Shutting down Orion API")


# ─────────────────────────────────────────────────────────────────────────
#  Application metadata (single source of truth)
# ─────────────────────────────────────────────────────────────────────────
APP_VERSION = "3.1.0"
APP_NAME    = "orion"


# ─────────────────────────────────────────────────────────────────────────
#  FastAPI app
# ─────────────────────────────────────────────────────────────────────────
# Sentry must be initialized BEFORE the FastAPI app is created so that the
# SDK can patch ASGI middleware. Safe no-op if SENTRY_DSN is not set.
init_sentry()

app = FastAPI(
    title="Orion API",
    description="White-label multi-tenant SaaS — Orion v3",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=cors_origin_regex(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id"],
    max_age=600,
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Security hardening: rate-limit handler, security headers, refresh-token registry.
# Documentation: docs/MASTER_GUIDE.md §8.
init_security(app)


# ─────────────────────────────────────────────────────────────────────────
#  Routers
# ─────────────────────────────────────────────────────────────────────────
app.include_router(auth_v3.router)
app.include_router(admin.router)
app.include_router(usuarios.router)
app.include_router(branding.router)
app.include_router(onboarding.router)
app.include_router(sucursales.router)
app.include_router(productos.router)
app.include_router(categorias.router)
app.include_router(ventas.router)
app.include_router(ordenes.router)
app.include_router(reportes.router)
app.include_router(inventario.router)
app.include_router(ml.router)
app.include_router(negocio.router)
app.include_router(ai.router)
app.include_router(payments.router)
app.include_router(mesas.router)
app.include_router(oai.router)
app.include_router(copilot.router)


# ─────────────────────────────────────────────────────────────────────────
#  Public meta endpoints
# ─────────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
def root():
    """API banner — points clients to the docs and health endpoints."""
    return {
        "name":        "Orion API",
        "version":     APP_VERSION,
        "docs":        "/docs",
        "openapi":     "/openapi.json",
        "health":      "/api/health",
    }


@app.get("/api/health", tags=["Health"])
def health_check():
    """Enriched liveness + readiness probe.

    Used by Render `healthCheckPath`, BetterStack uptime monitors and the
    smoke-test workflow. Returns 200 with structured payload when healthy,
    or 503 if the database connection is down (so deploys can fail fast).
    """
    db_ok = False
    db_error: str | None = None
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # pragma: no cover — exercised in incident response
        db_error = type(exc).__name__
    finally:
        db.close()

    payload = {
        "ok":      db_ok,
        "status":  "ok" if db_ok else "degraded",
        "service": APP_NAME,
        "version": APP_VERSION,
        "env":     os.getenv("ENV", "dev"),
        "db":      "ok" if db_ok else "error",
        "ts":      datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if db_error:
        payload["db_error"] = db_error
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content=payload,
    )
