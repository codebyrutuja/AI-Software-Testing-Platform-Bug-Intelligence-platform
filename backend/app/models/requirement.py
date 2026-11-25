"""
app/models/requirement.py
─────────────────────────
PURPOSE:
  Phase 4 Models for Software Requirements Management:
  1. RequirementDocument — Tracks uploaded PRDs/spec files (.md, .txt, .pdf)
  2. Requirement         — Structured individual requirements with project keys (e.g. AUTH-REQ-01)
  3. AcceptanceCriteria  — Testable criteria (Given-When-Then or itemized checks)
"""
import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class DocParsingStatus:
    PENDING = "pending"
    PARSED  = "parsed"
    FAILED  = "failed"
    ALL = (PENDING, PARSED, FAILED)


class RequirementCategory:
    FUNCTIONAL     = "functional"
    NON_FUNCTIONAL = "non_functional"
    SECURITY       = "security"
    UI_UX          = "ui_ux"
    PERFORMANCE    = "performance"
    ALL = (FUNCTIONAL, NON_FUNCTIONAL, SECURITY, UI_UX, PERFORMANCE)


class RequirementPriority:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"
    ALL = (LOW, MEDIUM, HIGH, CRITICAL)


class RequirementStatus:
    DRAFT      = "draft"
    APPROVED   = "approved"
    DEPRECATED = "deprecated"
    ALL = (DRAFT, APPROVED, DEPRECATED)


class RequirementDocument(Base):
    __tablename__ = "requirement_documents"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id      = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    uploaded_by     = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    filename        = Column(String(255), nullable=False)
    file_type       = Column(String(20), nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    raw_content     = Column(Text, nullable=True)
    parsing_status  = Column(
        Enum(*DocParsingStatus.ALL, name="docparsingstatus"),
        nullable=False,
        default=DocParsingStatus.PENDING,
        server_default="pending",
    )
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project      = relationship("Project", back_populates="documents")
    uploader     = relationship("User", foreign_keys=[uploaded_by])
    requirements = relationship("Requirement", back_populates="document")

    def __repr__(self):
        return f"<RequirementDocument id={self.id} filename={self.filename} status={self.parsing_status}>"


class Requirement(Base):
    __tablename__ = "requirements"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id  = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("requirement_documents.id", ondelete="SET NULL"), nullable=True, index=True)
    req_key     = Column(String(50), nullable=False)
    title       = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category    = Column(
        Enum(*RequirementCategory.ALL, name="requirementcategory"),
        nullable=False,
        default=RequirementCategory.FUNCTIONAL,
        server_default="functional",
        index=True,
    )
    priority    = Column(
        Enum(*RequirementPriority.ALL, name="requirementpriority"),
        nullable=False,
        default=RequirementPriority.MEDIUM,
        server_default="medium",
        index=True,
    )
    status      = Column(
        Enum(*RequirementStatus.ALL, name="requirementstatus"),
        nullable=False,
        default=RequirementStatus.DRAFT,
        server_default="draft",
        index=True,
    )
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project             = relationship("Project", back_populates="requirements")
    document            = relationship("RequirementDocument", back_populates="requirements")
    creator             = relationship("User", foreign_keys=[created_by])
    acceptance_criteria = relationship(
        "AcceptanceCriteria",
        back_populates="requirement",
        cascade="all, delete-orphan",
        order_by="AcceptanceCriteria.order_index",
    )
    test_cases = relationship("TestCase", back_populates="requirement")
    bugs       = relationship("Bug", back_populates="requirement")

    __table_args__ = (
        UniqueConstraint("project_id", "req_key", name="uq_project_req_key"),
    )

    def __repr__(self):
        return f"<Requirement id={self.id} req_key={self.req_key} title={self.title}>"


class AcceptanceCriteria(Base):
    __tablename__ = "acceptance_criteria"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True)
    criteria       = Column(Text, nullable=False)
    order_index    = Column(Integer, nullable=False, default=0, server_default="0")
    created_at     = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    requirement = relationship("Requirement", back_populates="acceptance_criteria")

    def __repr__(self):
        return f"<AcceptanceCriteria id={self.id} req_id={self.requirement_id} order={self.order_index}>"
