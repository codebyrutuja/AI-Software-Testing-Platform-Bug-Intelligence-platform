"""create bugs table

Revision ID: 006
Revises: 005
Create Date: 2026-11-21

Creates Phase 7 table:
- bugs — Defect management and bug tracking with links to test runs, cases, and requirements
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create PostgreSQL ENUM types
    bugseverity_enum = postgresql.ENUM(
        "critical", "high", "medium", "low",
        name="bugseverity",
        create_type=True,
    )
    bugseverity_enum.create(op.get_bind(), checkfirst=True)

    bugpriority_enum = postgresql.ENUM(
        "critical", "high", "medium", "low",
        name="bugpriority",
        create_type=True,
    )
    bugpriority_enum.create(op.get_bind(), checkfirst=True)

    bugstatus_enum = postgresql.ENUM(
        "open", "in_progress", "resolved", "closed", "wont_fix",
        name="bugstatus",
        create_type=True,
    )
    bugstatus_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create bugs table
    op.create_table(
        "bugs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_run_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_run_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("bug_key", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("steps_to_reproduce", sa.Text(), nullable=True),
        sa.Column("expected_behavior", sa.Text(), nullable=True),
        sa.Column("actual_behavior", sa.Text(), nullable=True),
        sa.Column("severity", sa.Enum("critical", "high", "medium", "low", name="bugseverity"), nullable=False, server_default="medium"),
        sa.Column("priority", sa.Enum("critical", "high", "medium", "low", name="bugpriority"), nullable=False, server_default="medium"),
        sa.Column("status", sa.Enum("open", "in_progress", "resolved", "closed", "wont_fix", name="bugstatus"), nullable=False, server_default="open"),
        sa.Column("environment", sa.String(100), nullable=True),
        sa.Column("browser_os", sa.String(255), nullable=True),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "bug_key", name="uq_project_bug_key"),
    )
    op.create_index("ix_bugs_project_id", "bugs", ["project_id"])
    op.create_index("ix_bugs_test_run_item_id", "bugs", ["test_run_item_id"])
    op.create_index("ix_bugs_test_case_id", "bugs", ["test_case_id"])
    op.create_index("ix_bugs_requirement_id", "bugs", ["requirement_id"])
    op.create_index("ix_bugs_status", "bugs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_bugs_status", table_name="bugs")
    op.drop_index("ix_bugs_requirement_id", table_name="bugs")
    op.drop_index("ix_bugs_test_case_id", table_name="bugs")
    op.drop_index("ix_bugs_test_run_item_id", table_name="bugs")
    op.drop_index("ix_bugs_project_id", table_name="bugs")
    op.drop_table("bugs")

    op.execute("DROP TYPE IF EXISTS bugstatus")
    op.execute("DROP TYPE IF EXISTS bugpriority")
    op.execute("DROP TYPE IF EXISTS bugseverity")
