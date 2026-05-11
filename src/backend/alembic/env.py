import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.db import Base, get_db_path
import app.db.models  # IMPORTANT

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        print("[alembic] Using injected connection")

        context.configure(
            connection=connectable,
            target_metadata=target_metadata,
            render_as_batch=True,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    else:
        # CLI usage — build our own engine using same path as the app
        db_path = get_db_path("MyEEGApp")
        print(f"[alembic] CLI mode — using DB: {db_path}")
        engine = engine_from_config(
            {"sqlalchemy.url": f"sqlite:///{db_path.as_posix()}"},
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        with engine.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
                compare_type=True,
            )
            with context.begin_transaction():
                context.run_migrations()


run_migrations_online()