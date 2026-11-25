"""
app/repositories/organization_repository.py
PURPOSE: All database queries for Organization and OrganizationMember tables.
The Storekeeper for multi-tenant workspace data.
"""
import logging
import re
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.organization import OrgRole, Organization, OrganizationMember
from app.schemas.organization import AddMemberRequest, OrganizationCreate, OrganizationUpdate

logger = logging.getLogger(__name__)


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Read Operations ─────────────────────────────────────────────────────────

    def get_by_id(self, org_id: str | UUID) -> Optional[Organization]:
        val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        return self.db.query(Organization).filter(Organization.id == val).first()

    def get_by_slug(self, slug: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.slug == slug).first()

    def get_user_organizations(self, user_id: str | UUID) -> List[Organization]:
        val = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
        return (
            self.db.query(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .filter(OrganizationMember.user_id == val)
            .filter(Organization.is_active == True)
            .all()
        )

    def get_member(self, org_id: str | UUID, user_id: str | UUID) -> Optional[OrganizationMember]:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        u_val = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
        return (
            self.db.query(OrganizationMember)
            .filter(
                OrganizationMember.organization_id == o_val,
                OrganizationMember.user_id == u_val,
            )
            .first()
        )

    def get_members(self, org_id: str | UUID) -> List[OrganizationMember]:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        return (
            self.db.query(OrganizationMember)
            .filter(OrganizationMember.organization_id == o_val)
            .all()
        )

    def is_member(self, org_id: str | UUID, user_id: str | UUID) -> bool:
        return self.get_member(org_id, user_id) is not None

    def get_member_role(self, org_id: str | UUID, user_id: str | UUID) -> Optional[str]:
        member = self.get_member(org_id, user_id)
        return member.role if member else None

    # ── Write Operations ─────────────────────────────────────────────────────────

    def _generate_unique_slug(self, name: str) -> str:
        base_slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
        slug = base_slug
        counter = 2
        while self.get_by_slug(slug):
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    def create(self, data: OrganizationCreate, created_by_id: str | UUID) -> Organization:
        slug = self._generate_unique_slug(data.name)
        creator_uuid = UUID(str(created_by_id)) if created_by_id else None
        org = Organization(
            name=data.name.strip(),
            slug=slug,
            description=data.description,
            is_active=True,
            created_by=creator_uuid,
        )
        self.db.add(org)
        self.db.flush()  # Get the org.id before committing

        # Creator automatically becomes the owner
        member = OrganizationMember(
            organization_id=org.id,
            user_id=creator_uuid,
            role=OrgRole.OWNER,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(org)
        logger.info(f"Created organization: {org.name} (slug={org.slug})")
        return org

    def add_member(self, org_id: str | UUID, user_id: str | UUID, role: str = OrgRole.MEMBER) -> OrganizationMember:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        u_val = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
        member = OrganizationMember(
            organization_id=o_val,
            user_id=u_val,
            role=role,
        )
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member
        self.db.add(member)
        self.db.commit()
        self.db.refresh(member)
        return member

    def update_member_role(self, org_id: str | UUID, user_id: str | UUID, new_role: str) -> bool:
        member = self.get_member(org_id, user_id)
        if not member:
            return False
        member.role = new_role
        self.db.commit()
        return True

    def remove_member(self, org_id: str | UUID, user_id: str | UUID) -> bool:
        member = self.get_member(org_id, user_id)
        if not member:
            return False
        self.db.delete(member)
        self.db.commit()
        return True

    def update(self, org_id: str | UUID, data: OrganizationUpdate) -> Optional[Organization]:
        org = self.get_by_id(org_id)
        if not org:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        self.db.commit()
        self.db.refresh(org)
        return org

    def deactivate(self, org_id: str | UUID) -> bool:
        org = self.get_by_id(org_id)
        if not org:
            return False
        org.is_active = False
        self.db.commit()
        return True
