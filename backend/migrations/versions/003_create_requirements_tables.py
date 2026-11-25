"""create requirement_documents, requirements, and acceptance_criteria tables

Revision ID: 003
Revises: 002
Create Date: 2026-11-21

Creates Phase 4 tables:
- requirement_documents
- requirements
- acceptance_criteria
"""
from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create PostgreSQL ENUM types
    docparsingstatus_enum = postgresql.ENUM(
        "pending", "parsed", "failed",
        name="docparsingstatus",
        create_type=True,
    )
    docparsingstatus_enum.create(op.get_bind(), checkfirst=True)

    reqcategory_enum = postgresql.ENUM(
        "functional", "non_functional", "security", "ui_ux", "performance",
        name="requirementcategory",
        create_type=True,
    )
    reqcategory_enum.create(op.get_bind(), checkfirst=True)

    reqpriority_enum = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="requirementpriority",
        create_type=True,
    )
    reqpriority_enum.create(op.get_bind(), checkfirst=True)

    reqstatus_enum = postgresql.ENUM(
        "draft", "approved", "deprecated",
        name="requirementstatus",
        create_type=True,
    )
    reqstatus_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create requirement_documents table
    op.create_table(
        "requirement_documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=True),
        sa.Column("parsing_status", sa.Enum("pending", "parsed", "failed", name="docparsingstatus"), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_req_docs_project_id", "requirement_documents", ["project_id"])

    # 3. Create requirements table
    op.create_table(
        "requirements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirement_documents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("req_key", sa.String(50), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Enum("functional", "non_functional", "security", "ui_ux", "performance", name="requirementcategory"), nullable=False, server_default="functional"),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="requirementpriority"), nullable=False, server_default="medium"),
        sa.Column("status", sa.Enum("draft", "approved", "deprecated", name="requirementstatus"), nullable=False, server_default="draft"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("project_id", "req_key", name="uq_project_req_key"),
    )
    op.create_index("ix_requirements_project_id", "requirements", ["project_id"])
    op.create_index("ix_requirements_category", "requirements", ["category"])
    op.create_index("ix_requirements_priority", "requirements", ["priority"])
    op.create_index("ix_requirements_status", "requirements", ["status"])

    # 4. Create acceptance_criteria table
    op.create_table(
        "acceptance_criteria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criteria", sa.Text(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_acceptance_criteria_req_id", "acceptance_criteria", ["requirement_id"])


def downgrade() -> None:
    op.drop_index("ix_acceptance_criteria_req_id", table_name="acceptance_criteria")
    op.drop_table("acceptance_criteria")

    op.drop_index("ix_requirements_status", table_name="requirements")
    op.drop_index("ix_requirements_priority", table_name="requirements")
    op.drop_index("ix_requirements_category", table_name="requirements")
    op.drop_index("ix_requirements_project_id", table_name="requirements")
    op.drop_table("requirements")

    op.drop_index("ix_req_docs_project_id", table_name="requirement_documents")
    op.drop_table("requirement_documents")

    op.execute("DROP TYPE IF EXISTS requirementstatus")
    op.execute("DROP TYPE IF EXISTS requirementpriority")
    op.execute("DROP TYPE IF EXISTS requirementcategory")
    op.execute("DROP TYPE IF EXISTS docparsingstatus")
