"""
app/models/test_run.py
──────────────────────
PURPOSE:
  Phase 6 Models for Test Execution Runs & Results Logging:
  1. TestRun       — An execution worksheet: "Sprint 24 Regression Run"
  2. TestRunItem   — One row per test case inside a run, records Pass/Fail/Blocked result

RELATIONSHIP TO PHASE 5:
  TestRun         belongs to → Project (Phase 3)
  TestRunItem     belongs to → TestRun  (Phase 6)
  TestRunItem     links to   → TestCase (Phase 5) — SET NULL on delete so history is preserved
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


class RunStatus:
    PLANNED     = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    ABORTED     = "aborted"
    ALL = (PLANNED, IN_PROGRESS, COMPLETED, ABORTED)


class RunEnvironment:
    LOCAL      = "local"
    STAGING    = "staging"
    QA         = "qa"
    PRODUCTION = "production"
    ALL = (LOCAL, STAGING, QA, PRODUCTION)


class RunResult:
    NOT_RUN = "not_run"
    PASSED  = "passed"
    FAILED  = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    ALL = (NOT_RUN, PASSED, FAILED, BLOCKED, SKIPPED)


class TestRun(Base):
    __tablename__ = "test_runs"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id   = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    run_key      = Column(String(50), nullable=False)
    name         = Column(String(255), nullable=False)
    description  = Column(Text, nullable=True)
    status       = Column(
        Enum(*RunStatus.ALL, name="runstatus"),
        nullable=False,
        default=RunStatus.PLANNED,
        server_default="planned",
        index=True,
    )
    environment  = Column(
        Enum(*RunEnvironment.ALL, name="runenvironment"),
        nullable=False,
        default=RunEnvironment.STAGING,
        server_default="staging",
    )
    created_by   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at   = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project  = relationship("Project", back_populates="test_runs")
    creator  = relationship("User", foreign_keys=[created_by])
    items    = relationship("TestRunItem", back_populates="test_run", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "run_key", name="uq_project_run_key"),
    )

    def __repr__(self):
        return f"<TestRun id={self.id} run_key={self.run_key} name={self.name}>"


class TestRunItem(Base):
    __tablename__ = "test_run_items"

    id                       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    test_run_id              = Column(UUID(as_uuid=True), ForeignKey("test_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    test_case_id             = Column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    executed_by              = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    result                   = Column(
        Enum(*RunResult.ALL, name="runresult"),
        nullable=False,
        default=RunResult.NOT_RUN,
        server_default="not_run",
        index=True,
    )
    failure_notes            = Column(Text, nullable=True)
    actual_duration_minutes  = Column(Integer, nullable=True)
    executed_at              = Column(DateTime(timezone=True), nullable=True)
    created_at               = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    test_run  = relationship("TestRun", back_populates="items")
    test_case = relationship("TestCase", back_populates="run_items")
    executor  = relationship("User", foreign_keys=[executed_by])
    bugs      = relationship("Bug", back_populates="test_run_item")

    def __repr__(self):
        return f"<TestRunItem id={self.id} run_id={self.test_run_id} result={self.result}>"
