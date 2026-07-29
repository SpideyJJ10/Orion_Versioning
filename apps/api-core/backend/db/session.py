"""
Motor SQLAlchemy — SQLite en desarrollo, PostgreSQL en producción (DATABASE_URL).
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import DATABASE_URL

_is_sqlite = DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False, "timeout": 30} if _is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Habilitar WAL en SQLite para mejor concurrencia y optimizar rendimiento
if _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB Cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """Dependency FastAPI: una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
