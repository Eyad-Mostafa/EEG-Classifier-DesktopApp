from __future__ import annotations

import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

logger = logging.getLogger(__name__)


def _find_alembic_dir() -> Path:
    """Locate alembic/ in dev and PyInstaller-packaged builds."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "alembic"
    return Path(__file__).resolve().parents[2] / "alembic"


def get_alembic_config() -> Config:
    alembic_dir = _find_alembic_dir()
    if not alembic_dir.exists():
        raise FileNotFoundError(f"alembic/ directory not found at: {alembic_dir}")

    cfg = Config()
    cfg.set_main_option("script_location", str(alembic_dir))
    return cfg


def upgrade_db(engine) -> None:
    """
    Apply all pending migrations. Safe to call on every startup.
    Injects the live engine connection so env.py uses the correct database.
    """
    cfg = get_alembic_config()
    logger.info("Running database migrations...")
    
    # Use connect(), NOT begin() — Alembic manages its own transaction
    with engine.connect() as connection:
        cfg.attributes["connection"] = connection
        command.upgrade(cfg, "head")
    
    logger.info("Migrations complete.")


def get_current_revision(engine) -> str | None:
    from alembic.runtime.migration import MigrationContext
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        return ctx.get_current_revision()