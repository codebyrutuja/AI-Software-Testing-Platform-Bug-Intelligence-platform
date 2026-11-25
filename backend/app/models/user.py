"""
app/models/user.py
───────────────────
PURPOSE:
  Defines the 'users' database table using SQLAlchemy ORM.
  This Python class = one row in the 'users' table.

WHY ORM (Object Relational Mapper)?
  Instead of writing raw SQL like:
      INSERT INTO users (id, email, ...) VALUES (...)
  We work with Python objects:
      user = User(email="a@b.com", ...)
      db.add(user)
  SQLAlchemy translates the Python to SQL automatically.

WHAT IS A MODEL?
  A model is a Python class that maps to a database table.
  Each class attribute = one column in the table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,       # For True/False columns
    Column,        # Defines a table column
    DateTime,      # For date+time columns
    Enum,          # For fixed-choice columns (like a dropdown)
    String,        # For text columns
)
from sqlalchemy.dialects.postgresql import UUID  # PostgreSQL-specific UUID type
from sqlalchemy.sql import func                   # SQL functions like NOW()

from app.core.database import Base  # The declarative base all models inherit from


# ── Role Enum ───────────────────────────────────────────────────────────────────
# Restricts the 'role' column to only these exact values.
# Using an Enum prevents typos like "Adminn" or "superAdmin" from sneaking in.
# These roles define what a user can do in the platform:
#   superadmin → manages the whole platform (users, billing)
#   admin      → manages an organization (projects, members)
#   member     → creates/runs tests, logs bugs
#   viewer     → read-only access (stakeholders, clients)
class UserRole:
    SUPERADMIN = "superadmin"
    ADMIN      = "admin"
    MEMBER     = "member"
    VIEWER     = "viewer"

    # All valid values as a tuple — used by SQLAlchemy Enum below
    ALL = ("superadmin", "admin", "member", "viewer")


# ── User Model ──────────────────────────────────────────────────────────────────
class User(Base):
    """
    Represents a row in the 'users' table.

    Inheriting from Base tells SQLAlchemy:
    "This class is a database table — scan it for Column definitions."
    """

    # __tablename__ tells SQLAlchemy what to name the table in PostgreSQL.
    # Convention: lowercase, plural of the model name.
    __tablename__ = "users"

    # ── Primary Key ─────────────────────────────────────────────────────────────
    # id is a UUID (Universally Unique Identifier).
    # WHY UUID instead of integer (1, 2, 3...)?
    #   - UUIDs are globally unique — safe to merge databases
    #   - Integers expose how many users you have (security risk)
    #   - UUIDs can be generated client-side before inserting
    #
    # default=uuid.uuid4 → Python generates a new UUID when creating a User object.
    # server_default=func.gen_random_uuid() → PostgreSQL generates one if Python doesn't.
    # (We use the Python default so it's available immediately in memory, not just after DB roundtrip)
    id = Column(
        UUID(as_uuid=True),          # Store as a real UUID type (not a string)
        primary_key=True,            # This column uniquely identifies each row
        default=uuid.uuid4,          # Auto-generate a UUID in Python
        nullable=False,              # Can never be NULL
    )

    # ── Email ────────────────────────────────────────────────────────────────────
    # The user's login identifier.
    # unique=True → no two users can have the same email (enforced by DB)
    # index=True  → creates a DB index for fast lookups by email (login is frequent)
    # nullable=False → email is mandatory
    email = Column(
        String(255),    # Max 255 characters (email standard limit)
        unique=True,    # Database-level uniqueness constraint
        index=True,     # Speeds up: SELECT * FROM users WHERE email = ?
        nullable=False,
    ) 

    # ── Password ─────────────────────────────────────────────────────────────────
    # We NEVER store plain text passwords.
    # hashed_password stores the bcrypt hash (e.g. "$2b$12$KIXkJZ...")
    # The hash is always 60 characters for bcrypt, but String(255) gives room.
    hashed_password = Column(
        String(255),
        nullable=False,
    )

    # ── Full Name ─────────────────────────────────────────────────────────────────
    # Optional display name shown in the UI.
    # nullable=True (default) → user can register without providing a name
    full_name = Column(
        String(255),
        nullable=True,
    )

    # ── Role ──────────────────────────────────────────────────────────────────────
    # Restricts the value to our defined roles using a PostgreSQL ENUM type.
    # name="userrole" → the name of the ENUM type in the PostgreSQL database.
    # This creates: CREATE TYPE userrole AS ENUM ('superadmin', 'admin', 'member', 'viewer');
    # default="member" → new users start as members (least privilege principle)
    role = Column(
        Enum(*UserRole.ALL, name="userrole"),
        nullable=False,
        default=UserRole.MEMBER,
    )

    # ── Active Status ─────────────────────────────────────────────────────────────
    # Soft-delete pattern: instead of deleting a user (which loses audit history),
    # we set is_active=False. Deactivated users cannot log in.
    # server_default="true" → PostgreSQL sets this to TRUE at the database level
    # even if Python forgets to set it.
    is_active = Column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    # ── Superadmin Flag ───────────────────────────────────────────────────────────
    # Separate from role for extra safety. Even if someone sets role="superadmin"
    # by accident, this boolean must also be True to get superadmin powers.
    # Only the first platform admin (seeded on startup) has this as True.
    is_superadmin = Column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )

    # ── Timestamps ────────────────────────────────────────────────────────────────
    # created_at: Set ONCE when the row is first inserted. Never changes.
    # server_default=func.now() → PostgreSQL itself sets this using NOW()
    # This is more reliable than Python's datetime.now() across timezones.
    created_at = Column(
        DateTime(timezone=True),   # Store with timezone info (UTC)
        server_default=func.now(), # DB sets this automatically on INSERT
        nullable=False,
    )

    # updated_at: Automatically updated every time the row changes.
    # onupdate=func.now() → SQLAlchemy calls NOW() on every UPDATE statement.
    # This creates a perfect audit trail of when data last changed.
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(), # Also set on INSERT
        onupdate=func.now(),       # Auto-updated on every UPDATE
        nullable=False,
    )

    # last_login_at: Tracks when the user last authenticated.
    # nullable=True → NULL until the user logs in for the first time.
    # We update this in the auth service after successful login.
    last_login_at = Column(
        DateTime(timezone=True),
        nullable=True,  # NULL = never logged in
    )

    # ── Python Representation ─────────────────────────────────────────────────────
    # __repr__ is what Python prints when you do: print(user)
    # Useful for debugging in logs and the Python shell.
    # We intentionally NEVER include hashed_password in __repr__ for security.
    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
