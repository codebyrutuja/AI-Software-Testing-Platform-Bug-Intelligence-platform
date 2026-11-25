"""
app/models/project.py
─────────────────────
PURPOSE: Software project model — each project belongs to one organization.
"""
import uuid
from sqlalchemy import Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class ProjectStatus:
    ACTIVE   = "active"
    ARCHIVED = "archived"
    ALL = ("active", "archived")


class Project(Base):
    __tablename__ = "projects"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name            = Column(String(255), nullable=False)
    key             = Column(String(10), nullable=False)
    description     = Column(Text, nullable=True)
    status          = Column(Enum(*ProjectStatus.ALL, name="projectstatus"), nullable=False, default=ProjectStatus.ACTIVE, server_default="active")
    created_by      = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="projects")
    requirements = relationship("Requirement", back_populates="project", cascade="all, delete-orphan")
    documents    = relationship("RequirementDocument", back_populates="project", cascade="all, delete-orphan")
    test_suites  = relationship("TestSuite", back_populates="project", cascade="all, delete-orphan")
    test_cases   = relationship("TestCase", back_populates="project", cascade="all, delete-orphan")
    test_runs    = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")
    bugs         = relationship("Bug", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("organization_id", "key", name="uq_project_key_per_org"),)

    def __repr__(self):
        return f"<Project id={self.id} key={self.key} name={self.name}>"
