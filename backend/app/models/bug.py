"""
app/models/bug.py
─────────────────
PURPOSE:
  Phase 7 Model for Bug Tracker & Defect Management.
  Records defects found during test runs, linked to test cases and requirements.
"""
import uuid
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class BugSeverity:
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    ALL = (CRITICAL, HIGH, MEDIUM, LOW)


class BugPriority:
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    ALL = (CRITICAL, HIGH, MEDIUM, LOW)


class BugStatus:
    OPEN        = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED    = "resolved"
    CLOSED      = "closed"
    WONT_FIX    = "wont_fix"
    ALL = (OPEN, IN_PROGRESS, RESOLVED, CLOSED, WONT_FIX)


class Bug(Base):
    __tablename__ = "bugs"

    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    project_id          = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    test_run_item_id    = Column(UUID(as_uuid=True), ForeignKey("test_run_items.id", ondelete="SET NULL"), nullable=True, index=True)
    test_case_id        = Column(UUID(as_uuid=True), ForeignKey("test_cases.id", ondelete="SET NULL"), nullable=True, index=True)
    requirement_id      = Column(UUID(as_uuid=True), ForeignKey("requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    bug_key             = Column(String(50), nullable=False)
    title               = Column(String(255), nullable=False)
    description         = Column(Text, nullable=True)
    steps_to_reproduce  = Column(Text, nullable=True)
    expected_behavior   = Column(Text, nullable=True)
    actual_behavior     = Column(Text, nullable=True)
    severity            = Column(
        Enum(*BugSeverity.ALL, name="bugseverity"),
        nullable=False,
        default=BugSeverity.MEDIUM,
        server_default="medium",
    )
    priority            = Column(
        Enum(*BugPriority.ALL, name="bugpriority"),
        nullable=False,
        default=BugPriority.MEDIUM,
        server_default="medium",
    )
    status              = Column(
        Enum(*BugStatus.ALL, name="bugstatus"),
        nullable=False,
        default=BugStatus.OPEN,
        server_default="open",
        index=True,
    )
    environment         = Column(String(100), nullable=True)
    browser_os          = Column(String(255), nullable=True)
    reported_by         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    reported_at         = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    resolved_at         = Column(DateTime(timezone=True), nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project        = relationship("Project", back_populates="bugs")
    test_run_item  = relationship("TestRunItem", back_populates="bugs")
    test_case      = relationship("TestCase", back_populates="bugs")
    requirement    = relationship("Requirement", back_populates="bugs")
    reporter       = relationship("User", foreign_keys=[reported_by])
    assignee       = relationship("User", foreign_keys=[assigned_to])

    __table_args__ = (
        UniqueConstraint("project_id", "bug_key", name="uq_project_bug_key"),
    )

    def __repr__(self):
        return f"<Bug id={self.id} bug_key={self.bug_key} title={self.title}>"
