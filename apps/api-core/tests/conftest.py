"""
Pytest fixtures for Orion POS backend tests.

Strategy
--------
- One in-memory SQLite engine per test session, shared via StaticPool.
- All tables created from SQLAlchemy metadata at session start (no Alembic in tests).
- The FastAPI dependency `get_db` is overridden to use this engine.
- A `db_session` fixture gives tests direct DB access for setup/asserts.
- `tenant_factory` builds full tenants (with branding, sucursal, owner) on demand.
- `client` is a TestClient against the FastAPI app with overrides applied.
"""
from __future__ import annotations

import os
from typing import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Set required env vars BEFORE importing app modules. These avoid "weak default"
# warnings and keep behavior deterministic across runs.
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only-do-not-use-in-prod")
os.environ.setdefault("ADMIN_PIN", "9999")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from backend.auth_v3.passwords import hash_password  # noqa: E402
from backend.auth_v3.tokens import emitir_par_tokens  # noqa: E402
from backend.db.session import Base, get_db  # noqa: E402
from backend.main import app  # noqa: E402
from backend.models.orm import (  # noqa: E402
    OnboardingProgress,
    Sucursal,
    Tenant,
    TenantBranding,
    Usuario,
)


# ─────────────────────────────────────────────────────────────────────────
#  ENGINE & SESSION (in-memory SQLite, shared across the whole session)
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def engine():
    """Single in-memory SQLite engine shared by all tests in the session."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Enable FK enforcement (SQLite has it off by default)
    @event.listens_for(eng, "connect")
    def _fk_pragma(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="session")
def TestingSessionLocal(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def _truncate_db(engine):
    """Truncate every table BEFORE each test so they are isolated.

    We truncate (DELETE FROM) instead of recreating to keep things fast.
    """
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.exec_driver_sql(f"DELETE FROM {table.name}")
    yield


@pytest.fixture()
def db_session(TestingSessionLocal) -> Iterator[Session]:
    """Direct DB session for tests (setup/asserts)."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ─────────────────────────────────────────────────────────────────────────
#  FASTAPI CLIENT (overrides get_db)
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def client(TestingSessionLocal) -> Iterator[TestClient]:
    def _override_get_db():
        s = TestingSessionLocal()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────────────────
#  HELPER FACTORIES
# ─────────────────────────────────────────────────────────────────────────
def _new_tenant(
    db: Session,
    *,
    email: str,
    password: str = "secret123",
    nombre: str = "Negocio Test",
    es_admin: bool = False,
    plan_activo: bool = True,
    nicho: str = "restaurante",
) -> dict:
    """Create a Tenant + Branding + Onboarding + default Sucursal + Owner Usuario.

    Returns dict with all the created entities for convenience.
    """
    pwd_hash = hash_password(password)

    tenant = Tenant(
        email         = email,
        password_hash = pwd_hash,
        nombre        = nombre,
        plan          = "admin" if es_admin else "starter",
        es_admin      = es_admin,
        plan_activo   = plan_activo,
    )
    db.add(tenant)
    db.flush()

    db.add(TenantBranding(
        tenant_id        = tenant.id,
        nombre_comercial = nombre,
        nicho            = nicho,
    ))
    db.add(OnboardingProgress(tenant_id=tenant.id))

    sucursal = Sucursal(tenant_id=tenant.id, nombre="Principal")
    db.add(sucursal)
    db.flush()

    rol = "super_admin" if es_admin else "owner"
    owner = Usuario(
        tenant_id     = tenant.id,
        email         = email,
        password_hash = pwd_hash,
        nombre        = "Owner Test",
        rol           = rol,
        sucursal_id   = sucursal.id,
        activo        = True,
    )
    db.add(owner)
    db.commit()
    db.refresh(tenant)
    db.refresh(sucursal)
    db.refresh(owner)

    return {
        "tenant":   tenant,
        "sucursal": sucursal,
        "owner":    owner,
        "password": password,
    }


def _make_auth_headers(usuario: Usuario) -> dict[str, str]:
    """Build Authorization headers using the v3 token (works for productos/ordenes too)."""
    pair = emitir_par_tokens(usuario)
    return {"Authorization": f"Bearer {pair['access_token']}"}


def _make_admin_headers(tenant_data: dict) -> dict[str, str]:
    """Build admin auth headers using a v3 token issued for the super_admin Usuario.

    `tenant_data` is the dict returned by `_new_tenant`, which includes the
    super_admin Usuario at the `owner` key when `es_admin=True`.
    """
    pair = emitir_par_tokens(tenant_data["owner"])
    return {"Authorization": f"Bearer {pair['access_token']}"}


# ─────────────────────────────────────────────────────────────────────────
#  PUBLIC FIXTURES
# ─────────────────────────────────────────────────────────────────────────
@pytest.fixture()
def tenant_factory(db_session):
    """Factory fixture: call to create a tenant with all related rows."""
    counter = {"i": 0}

    def make(**overrides) -> dict:
        counter["i"] += 1
        defaults = {
            "email":  f"tenant{counter['i']}@test.com",
            "nombre": f"Tenant {counter['i']}",
        }
        defaults.update(overrides)
        return _new_tenant(db_session, **defaults)

    return make


@pytest.fixture()
def tenant_owner(tenant_factory):
    """A regular tenant with an owner ready to login."""
    return tenant_factory(email="owner@test.com", nombre="Negocio Demo")


@pytest.fixture()
def tenant_admin(tenant_factory):
    """A super_admin tenant (Orion staff). Uses a real-looking TLD to satisfy EmailStr."""
    return tenant_factory(email="admin@orion.app", nombre="Orion Admin", es_admin=True)


@pytest.fixture()
def auth_headers_owner(tenant_owner):
    return _make_auth_headers(tenant_owner["owner"])


@pytest.fixture()
def admin_headers(tenant_admin):
    return _make_admin_headers(tenant_admin)


@pytest.fixture()
def make_auth_headers():
    """Helper to build headers from any Usuario instance."""
    return _make_auth_headers
