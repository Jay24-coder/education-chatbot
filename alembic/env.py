"""
Alembic environment: runs migrations against the same Postgres as the app.

The database URL is built from app config (postgres_* settings), using the
sync driver (psycopg2) so migrations run from the CLI without an event loop.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.engine import Connection

# Add project root so `app` is importable.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import db_redis

# Alembic Config object
config = context.config

# Build sync URL from app settings (same host/db/user as the app).
# App uses postgresql+asyncpg; Alembic uses postgresql+psycopg2 for sync CLI.
_sync_url = db_redis.build_postgres_url().replace("postgresql+asyncpg://", "postgresql+psycopg2://")
config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# No MetaData / autogenerate in this project (we use raw SQL migrations).
# If you add SQLAlchemy models later, assign target_metadata for autogenerate.
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode: only emit SQL to a script."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode: connect to DB and run migrations."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
