"""
app/models/test_case.py
───────────────────────
PURPOSE:
  Phase 5 Models for Test Cases & Test Suites Management:
  1. TestSuite  — Hierarchical folders for grouping test cases by feature/module
  2. TestCase   — Structured test cases with sequential keys (e.g. AUTH-TC-01)
  3. TestStep   — Itemized step-by-step procedures (Action, Test Data, Expected Result)
"""
import uuid
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class TestType:
    MANUAL     = "manual"
    AUTOMATED  = "automated"
    REGRESSION = "regression"
    SMOKE      = "smoke"
    SANITY     = "sanity"
    ALL = (MANUAL, AUTOMATED, REGRESSION, SMOKE, SANITY)


class TestPriority:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"
    ALL = (LOW, MEDIUM, HIGH, CRITICAL)


class TestStatus:
    DRAFT      = "draft"
    ACTIVE     = "active"
    DEPRECATED = "deprecated"
    ALL = (DRAFT, ACTIVE, DEPRECATED)


class TestSuite(Base):
    __tablename__ = "test_suites"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id      = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_suite_id = Column(UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="CASCADE"), nullable=True, index=True)
    name            = Column(String(255), nullable=False)
    description     = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    project      = relationship("Project", back_populates="test_suites")
    parent_suite = relationship("TestSuite", remote_side=[id], back_populates="sub_suites")
    sub_suites   = relationship("TestSuite", back_populates="parent_suite", cascade="all, delete-orphan")
    test_cases   = relationship("TestCase", back_populates="suite", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<TestSuite id={self.id} name={self.name}>"


class TestCase(Base):
    __tablename__ = "test_cases"

    id                         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id                 = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_id                   = Column(UUID(as_uuid=True), ForeignKey("test_suites.id", ondelete="SET NULL"), nullable=True, index=True)
    requirement_id             = Column(UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    tc_key                     = Column(String(50), nullable=False)
    title                      = Column(String(255), nullable=False)
    description                = Column(Text, nullable=True)
    preconditions              = Column(Text, nullable=True)
    test_type                  = Column(
        Enum(*TestType.ALL, name="testtype"),
        nullable=False,
        default=TestType.MANUAL,
        server_default="manual",
    )
    priority                   = Column(
        Enum(*TestPriority.ALL, name="testpriority"),
        nullable=False,
        default=TestPriority.MEDIUM,
        server_default="medium",
        index=True,
    )
    status                     = Column(
        Enum(*TestStatus.ALL, name="teststatus"),
        nullable=False,
        default=TestStatus.ACTIVE,
        server_default="active",
        index=True,
    )
    estimated_duration_minutes = Column(Integer, default=5, server_default="5", nullable=False)
    created_by                 = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at                 = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at                 = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project     = relationship("Project", back_populates="test_cases")
    suite       = relationship("TestSuite", back_populates="test_cases")
    requirement = relationship("Requirement", back_populates="test_cases")
    creator     = relationship("User", foreign_keys=[created_by])
    steps       = relationship(
        "TestStep",
        back_populates="test_case",
        cascade="all, delete-orphan",
        order_by="TestStep.step_number",
    )
    run_items   = relationship("TestRunItem", back_populates="test_case")
    bugs        = relationship("Bug", back_populates="test_case")

    __table_args__ = (
        UniqueConstraint("project_id", "tc_key", name="uq_project_tc_key"),
    )

    def __repr__(self):
        return f"<TestCase id={self.id} tc_key={self.tc_key} title={self.title}>"


class TestStep(Base):
    __tablename__ = "test_steps"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    test_case_id    = Column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number     = Column(Integer, nullable=False)
    action          = Column(Text, nullable=False)
    test_data       = Column(Text, nullable=True)
    expected_result = Column(Text, nullable=False)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test_case = relationship("TestCase", back_populates="steps")

    def __repr__(self):
        return f"<TestStep id={self.id} tc_id={self.test_case_id} step={self.step_number}>"
