"""Alembic environment configuration for asset-service.

Reads DATABASE_URL from the app's own Settings (app/config.py) rather
than duplicating it in alembic.ini - one source of truth for the
connection string, matching how the app itself connects.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.db.session import Base  # noqa: E402

# Explicit imports, not relying on some other import path (a router) to
# have already pulled these in first - target_metadata below only sees
# a model if it's been imported somewhere in this process BEFORE this
# line runs. Without this, autogenerate can silently produce an empty
# migration for a genuinely new model - the exact lesson already
# learned once in ml-service's own migration history (see that
# service's alembic/env.py). All four of this service's models live in
# one module, so a single import covers everything.
from app.models.asset import Asset, AssetType, Facility, MetricDefinition  # noqa: E402, F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
