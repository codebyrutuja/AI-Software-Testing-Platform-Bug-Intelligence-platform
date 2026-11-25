"""
app/core/database.py
─────────────────────
PURPOSE:
  Sets up the SQLAlchemy database connection and session factory.
  Every API request gets its own database session via dependency injection.

HOW IT WORKS:
  1. create_engine() — Creates a connection pool to PostgreSQL.
  2. SessionLocal — A factory that creates individual database sessions.
  3. get_db() — A FastAPI dependency. It creates a session, hands it to the
     endpoint, and closes it cleanly when the request finishes.
  4. Base — All SQLAlchemy models inherit from this, so SQLAlchemy knows
     which Python classes correspond to database tables.

WHY SESSION PER REQUEST?
  Each HTTP request is isolated. If two requests run simultaneously, they
  each get their own database session. This prevents data from one request
  leaking into another (thread safety).
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.core.config import settings

# ── Engine ──────────────────────────────────────────────────────────────────────
# The engine manages the connection pool to PostgreSQL.
# pool_pre_ping=True: Before using a connection, check if it's still alive.
# This handles database restarts gracefully.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # Log all SQL statements in debug mode
)

# ── Session Factory ─────────────────────────────────────────────────────────────
# SessionLocal is a class. Each call to SessionLocal() creates a new session.
# autocommit=False: We control transactions manually (begin/commit/rollback).
# autoflush=False: Don't automatically send changes to DB within a transaction.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# ── Base Class ──────────────────────────────────────────────────────────────────
# All SQLAlchemy model classes (tables) will inherit from Base.
# This lets SQLAlchemy discover all tables and create them.
Base = declarative_base()


# ── Dependency ──────────────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session for each request.

    Usage in an endpoint:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...

    The 'yield' makes this a context manager:
    - Code before yield: creates the session (setup)
    - yield: hands the session to the endpoint
    - Code after yield (finally): closes the session (cleanup)
    This guarantees the session is ALWAYS closed, even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

