from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()
_engine = None
SessionLocal: Optional[sessionmaker] = None


def get_db_path(app_name: str = "MyEEGApp") -> Path:
    """
    Cross-platform user data path for the SQLite file.
    Uses platformdirs if available, otherwise falls back to ~/.{app_name}/data.sqlite
    """
    try:
        from platformdirs import user_data_dir
        data_dir = Path(user_data_dir(app_name, appauthor=False))
    except Exception:
        data_dir = Path.home() / f".{app_name.lower()}"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "data.sqlite"


def get_engine(db_path: Path):
    """Return SQLAlchemy engine for given sqlite path (absolute)."""
    db_path.parent.mkdir(parents=True, exist_ok=True)  # safety
    url = f"sqlite:///{db_path.as_posix()}"
    return create_engine(url, connect_args={"check_same_thread": False}, future=True)


def _on_connect_sqlite(dbapi_conn, connection_record):
    """Enable useful pragmas for SQLite on every new connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    cursor.execute("PRAGMA journal_mode = WAL;")  # optional but often useful
    cursor.close()


def init_db(app_name: str = "MyEEGApp"):
    """
    Initialize engine + session factory only.
    Migrations are handled separately.
    """
    global _engine, SessionLocal

    db_path = get_db_path(app_name)
    _engine = get_engine(db_path)

    event.listen(_engine, "connect", _on_connect_sqlite)

    SessionLocal = sessionmaker(
        bind=_engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )

    return _engine


def get_session():
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return SessionLocal()
