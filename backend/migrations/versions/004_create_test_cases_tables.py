"""create test_suites, test_cases, and test_steps tables

Revision ID: 004
Revises: 003
Create Date: 2026-11-21

Creates Phase 5 tables:
- test_suites
- test_cases
- test_steps
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create PostgreSQL ENUM types
    testtype_enum = postgresql.ENUM(
        "manual", "automated", "regression", "smoke", "sanity",
        name="testtype",
        create_type=True,
    )
    testtype_enum.create(op.get_bind(), checkfirst=True)

    testpriority_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="testpriority",
        create_type=True,
    )
    testpriority_enum.create(op.get_bind(), checkfirst=True)

    teststatus_enum = postgresql.ENUM(
        "draft", "active", "deprecated",
        name="teststatus",
        create_type=True,
    )
    teststatus_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create test_suites table
    op.create_table(
        "test_suites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("parent_suite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_test_suites_project_id", "test_suites", ["project_id"])
    op.create_index("ix_test_suites_parent_suite_id", "test_suites", ["parent_suite_id"])

    # 3. Create test_cases table
    op.create_table(
        "test_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("suite_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_suites.id", ondelete="SET NULL"), nullable=True),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True),
        sa.Column("tc_key", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("preconditions", sa.Text(), nullable=True),
        sa.Column("test_type", sa.Enum("manual", "automated", "regression", "smoke", "sanity", name="testtype"), nullable=False, server_default="manual"),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="testpriority"), nullable=False, server_default="medium"),
        sa.Column("status", sa.Enum("draft", "active", "deprecated", name="teststatus"), nullable=False, server_default="active"),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "tc_key", name="uq_project_tc_key"),
    )
    op.create_index("ix_test_cases_project_id", "test_cases", ["project_id"])
    op.create_index("ix_test_cases_suite_id", "test_cases", ["suite_id"])
    op.create_index("ix_test_cases_requirement_id", "test_cases", ["requirement_id"])
    op.create_index("ix_test_cases_priority", "test_cases", ["priority"])
    op.create_index("ix_test_cases_status", "test_cases", ["status"])

    # 4. Create test_steps table
    op.create_table(
        "test_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("test_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("test_data", sa.Text(), nullable=True),
        sa.Column("expected_result", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_test_steps_test_case_id", "test_steps", ["test_case_id"])


def downgrade() -> None:
    op.drop_index("ix_test_steps_test_case_id", table_name="test_steps")
    op.drop_table("test_steps")

    op.drop_index("ix_test_cases_status", table_name="test_cases")
    op.drop_index("ix_test_cases_priority", table_name="test_cases")
    op.drop_index("ix_test_cases_requirement_id", table_name="test_cases")
    op.drop_index("ix_test_cases_suite_id", table_name="test_cases")
    op.drop_index("ix_test_cases_project_id", table_name="test_cases")
    op.drop_table("test_cases")

    op.drop_index("ix_test_suites_parent_suite_id", table_name="test_suites")
    op.drop_index("ix_test_suites_project_id", table_name="test_suites")
    op.drop_table("test_suites")

    op.execute("DROP TYPE IF EXISTS teststatus")
    op.execute("DROP TYPE IF EXISTS testpriority")
    op.execute("DROP TYPE IF EXISTS testtype")
