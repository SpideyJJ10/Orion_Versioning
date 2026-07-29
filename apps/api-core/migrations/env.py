"""
Alembic environment configuration.

Loads DATABASE_URL from backend.core.config and uses Base.metadata for autogenerate.
Supports both online (live DB) and offline (emit SQL) modes.
"""
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make repo root importable so `backend.*` resolves ─────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Project imports (after sys.path tweak)
from backend.core.config import DATABASE_URL  # noqa: E402
from backend.db.session import Base  # noqa: E402
from backend.models import orm as _orm  # noqa: E402, F401  ensure all models registered

# Alembic Config object
config = context.config

# Inject the DATABASE_URL at runtime (overrides empty sqlalchemy.url in alembic.ini)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for 'autogenerate'
target_metadata = Base.metadata


def _is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL without DBAPI connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=_is_sqlite_url(url or ""),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live database)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        is_sqlite = connection.dialect.name == "sqlite"
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=is_sqlite,  # SQLite needs batch mode for ALTER
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
