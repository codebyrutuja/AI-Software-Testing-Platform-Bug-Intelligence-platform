"""
app/models/organization.py
─────────────────────────
PURPOSE: Organization workspace and member models for Phase 3 multi-tenancy.
"""
import uuid
from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class OrgRole:
    OWNER  = "owner"
    ADMIN  = "admin"
    MEMBER = "member"
    VIEWER = "viewer"
    ALL = ("owner", "admin", "member", "viewer")


class Organization(Base):
    __tablename__ = "organizations"

    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    name        = Column(String(255), nullable=False)
    slug        = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active   = Column(Boolean, default=True, server_default="true", nullable=False)
    created_by  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    members  = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="organization", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Organization id={self.id} name={self.name} slug={self.slug}>"


class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    user_id         = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role            = Column(Enum(*OrgRole.ALL, name="orgrole"), nullable=False, default=OrgRole.MEMBER)
    joined_at       = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    organization = relationship("Organization", back_populates="members")
    user         = relationship("User")

    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_org_member"),)

    def __repr__(self):
        return f"<OrganizationMember org={self.organization_id} user={self.user_id} role={self.role}>"
