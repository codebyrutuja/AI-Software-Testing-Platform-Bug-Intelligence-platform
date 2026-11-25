"""create users table

Revision ID: 001
Revises: 
Create Date: 2026-11-16

Creates the initial 'users' table with all columns needed for Phase 2 auth.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None   # This is the FIRST migration (no parent)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the users table and userrole enum type."""

    # Create the PostgreSQL ENUM type first
    # This must be created before the table that uses it
    userrole_enum = postgresql.ENUM(
        "superadmin", "admin", "member", "viewer",
        name="userrole",
        create_type=True,
    )
    userrole_enum.create(op.get_bind(), checkfirst=True)

    # Create the users table
    op.create_table(
        "users",
        # Primary key: UUID
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        # Login identifier
        sa.Column("email", sa.String(255), nullable=False),
        # Bcrypt hash — never plain text
        sa.Column("hashed_password", sa.String(255), nullable=False),
        # Display name (optional)
        sa.Column("full_name", sa.String(255), nullable=True),
        # Role enum
        sa.Column(
            "role",
            sa.Enum("superadmin", "admin", "member", "viewer", name="userrole"),
            nullable=False,
            server_default="member",
        ),
        # Soft-delete flag
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        # Platform superadmin flag
        sa.Column("is_superadmin", sa.Boolean(), nullable=False, server_default="false"),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Unique constraint on email (enforced at DB level)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # Regular index on id for fast lookups by primary key (auto-created for PK,
    # but explicit here for documentation clarity)
    op.create_index("ix_users_id", "users", ["id"], unique=False)


def downgrade() -> None:
    """Drop the users table and userrole enum type."""
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    # Drop the enum type after the table is gone
    op.execute("DROP TYPE IF EXISTS userrole")
