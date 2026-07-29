# Migrations — Alembic

This directory holds all schema migrations for the Orion POS database.

## Quick reference

```powershell
# Apply all pending migrations
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Create a new auto-generated migration after editing models
alembic revision --autogenerate -m "describe what changed"

# Show current revision
alembic current

# Show migration history
alembic history --verbose
```

## Conventions

- Filenames are timestamped + slugged automatically via `alembic.ini :: file_template`.
- Revision IDs are short hashes; `down_revision` chains them.
- For SQLite we use `render_as_batch=True` (configured in `env.py`) to support `ALTER TABLE`.
- Always test migrations on a copy of production data before deploying.

## First-time setup on a new environment

```powershell
pip install -r requirements.txt
$env:DATABASE_URL = "sqlite:///./tizon.db"   # or your Postgres URL
alembic upgrade head
```

The legacy `Base.metadata.create_all(...)` call in `backend/main.py` is kept as a
no-op safeguard for tables that may exist outside Alembic-managed schema.
