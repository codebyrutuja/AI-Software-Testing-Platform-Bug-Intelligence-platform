"""create test_runs and test_run_items tables

Revision ID: 005
Revises: 004
Create Date: 2026-11-21

Creates Phase 6 tables:
- test_runs        — Execution worksheets (Sprint Regression Run, Smoke Test, etc.)
- test_run_items   — One row per test case inside a run, records Pass/Fail/Blocked result
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create PostgreSQL ENUM types
    runstatus_enum = postgresql.ENUM(
        "planned", "in_progress", "completed", "aborted",
        name="runstatus",
        create_type=True,
    )
    runstatus_enum.create(op.get_bind(), checkfirst=True)

    runenvironment_enum = postgresql.ENUM(
        "local", "staging", "qa", "production",
        name="runenvironment",
        create_type=True,
    )
    runenvironment_enum.create(op.get_bind(), checkfirst=True)

    runresult_enum = postgresql.ENUM(
        "not_run", "passed", "failed", "blocked", "skipped",
        name="runresult",
        create_type=True,
    )
    runresult_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create test_runs table
    op.create_table(
        "test_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("run_key", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("planned", "in_progress", "completed", "aborted", name="runstatus"), nullable=False, server_default="planned"),
        sa.Column("environment", sa.Enum("local", "staging", "qa", "production", name="runenvironment"), nullable=False, server_default="staging"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "run_key", name="uq_project_run_key"),
    )
    op.create_index("ix_test_runs_project_id", "test_runs", ["project_id"])
    op.create_index("ix_test_runs_status", "test_runs", ["status"])

    # 3. Create test_run_items table
    op.create_table(
        "test_run_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("test_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("executed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("result", sa.Enum("not_run", "passed", "failed", "blocked", "skipped", name="runresult"), nullable=False, server_default="not_run"),
        sa.Column("failure_notes", sa.Text(), nullable=True),
        sa.Column("actual_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_test_run_items_test_run_id", "test_run_items", ["test_run_id"])
    op.create_index("ix_test_run_items_test_case_id", "test_run_items", ["test_case_id"])
    op.create_index("ix_test_run_items_result", "test_run_items", ["result"])


def downgrade() -> None:
    op.drop_index("ix_test_run_items_result", table_name="test_run_items")
    op.drop_index("ix_test_run_items_test_case_id", table_name="test_run_items")
    op.drop_index("ix_test_run_items_test_run_id", table_name="test_run_items")
    op.drop_table("test_run_items")

    op.drop_index("ix_test_runs_status", table_name="test_runs")
    op.drop_index("ix_test_runs_project_id", table_name="test_runs")
    op.drop_table("test_runs")

    op.execute("DROP TYPE IF EXISTS runresult")
    op.execute("DROP TYPE IF EXISTS runenvironment")
    op.execute("DROP TYPE IF EXISTS runstatus")
