"""Alembic environment configuration for ml-service.

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

# Explicit imports, not relying on some other import path (a router, the
# scheduler) to have already pulled these in first - target_metadata
# below only sees a model if it's been imported somewhere in this
# process BEFORE this line runs. Without this, autogenerate can silently
# produce an empty migration for a genuinely new model, which is a
# confusing, hard-to-diagnose failure mode (found while adding
# Prediction - AssetBaseline's own migration apparently worked
# previously via a less robust, accidental import chain, not this
# explicit one).
from app.models.asset_baseline import AssetBaseline  # noqa: E402, F401
from app.models.prediction import Prediction  # noqa: E402, F401

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
