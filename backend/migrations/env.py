"""
migrations/env.py
──────────────────
PURPOSE:
  This is Alembic's environment configuration.
  It tells Alembic HOW to connect to the database and WHICH models to track.

  Alembic runs this file every time you run:
    alembic upgrade head    ← applies migrations
    alembic revision --autogenerate  ← generates new migration from model changes
    alembic downgrade -1  ← rolls back one migration
"""

import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Add backend/ to Python path ─────────────────────────────────────────────────
# This allows Alembic to import our app modules (app.core.config, app.models, etc.)
# Without this, running `alembic upgrade head` from the backend/ directory would
# fail with ModuleNotFoundError.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import app settings ──────────────────────────────────────────────────────────
# We load DATABASE_URL from our app's settings (reads from .env file).
# This ensures Alembic uses the SAME database as the running application.
from app.core.config import settings

# ── Import ALL models ────────────────────────────────────────────────────────────
# CRITICAL: Alembic detects schema changes by comparing the current database
# state against the SQLAlchemy metadata (Base.metadata).
# If a model is NOT imported here, Alembic won't see it → won't generate migrations for it.
# We import from app.models.__init__ which re-exports everything.
import app.models  # noqa: F401 — imports User, UserRole (and future models)
from app.core.database import Base  # The declarative base all models inherit from

# ── Alembic Config ───────────────────────────────────────────────────────────────
# `config` is the alembic.Config object (reads alembic.ini)
config = context.config

# Set up Python logging from alembic.ini's [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# IMPORTANT: Override the sqlalchemy.url from alembic.ini with our real DATABASE_URL
# This means we never hardcode database credentials in alembic.ini (which is in Git).
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# `target_metadata` is what Alembic compares against the live database.
# Base.metadata contains all table definitions from our SQLAlchemy models.
target_metadata = Base.metadata


# ── Offline Mode ─────────────────────────────────────────────────────────────────
# "Offline" = generates SQL scripts without connecting to the database.
# Used for: generating migration scripts to review before applying.
# Run with: alembic upgrade head --sql
def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # Detect column type changes
        compare_server_default=True,  # Detect server_default changes
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online Mode ───────────────────────────────────────────────────────────────────
# "Online" = connects to the real database and runs migrations directly.
# This is the normal mode used in development and production.
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Don't pool connections during migrations
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # Detect column type changes (e.g. String→Text)
            compare_server_default=True,  # Detect server_default changes
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry Point ───────────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
