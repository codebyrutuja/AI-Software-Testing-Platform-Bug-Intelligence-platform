"""
app/services/organization_service.py
─────────────────────────────────────
PURPOSE:
  Business logic for Organization workspaces and membership management.
  Sits between the API router and OrganizationRepository.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import OrgRole, Organization, OrganizationMember
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.user_repository import UserRepository
from app.schemas.organization import (
    AddMemberRequest,
    MemberResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)

logger = logging.getLogger(__name__)


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.user_repo = UserRepository(db)

    def create_organization(
        self, data: OrganizationCreate, current_user: User
    ) -> OrganizationResponse:
        """
        Creates a new organization workspace.
        Business Rules:
        1. Slug is automatically derived from the name and made unique.
        2. The creator automatically becomes the first member with role='owner'.
        """
        org = self.org_repo.create(data, created_by_id=current_user.id)
        logger.info(f"User {current_user.email} created organization '{org.name}' ({org.id})")
        return OrganizationResponse.model_validate(org)

    def get_my_organizations(self, current_user: User) -> List[OrganizationResponse]:
        """
        Returns all organizations the current user belongs to.
        Superadmin sees all organizations if desired, or their own.
        """
        orgs = self.org_repo.get_user_organizations(current_user.id)
        return [OrganizationResponse.model_validate(o) for o in orgs]

    def get_organization(
        self, org_id: str | UUID, current_user: User
    ) -> OrganizationResponse:
        """
        Retrieves organization details.
        Requires the user to be a member of the organization (or superadmin).
        """
        org = self.org_repo.get_by_id(org_id)
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        if not current_user.is_superadmin and not self.org_repo.is_member(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )

        return OrganizationResponse.model_validate(org)

    def update_organization(
        self, org_id: str | UUID, data: OrganizationUpdate, current_user: User
    ) -> OrganizationResponse:
        """
        Updates organization profile/name.
        Requires owner or admin role.
        """
        org = self.org_repo.get_by_id(org_id)
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        role = self.org_repo.get_member_role(org_id, current_user.id)
        if not current_user.is_superadmin and role not in (OrgRole.OWNER, OrgRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners or admins can update organization settings.",
            )

        updated_org = self.org_repo.update(org_id, data)
        return OrganizationResponse.model_validate(updated_org)

    def get_members(
        self, org_id: str | UUID, current_user: User
    ) -> List[MemberResponse]:
        """
        Lists all members of the organization.
        Requires the user to be a member of the organization.
        """
        if not current_user.is_superadmin and not self.org_repo.is_member(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )

        members = self.org_repo.get_members(org_id)
        return [MemberResponse.model_validate(m) for m in members]

    def add_member(
        self, org_id: str | UUID, request: AddMemberRequest, current_user: User
    ) -> MemberResponse:
        """
        Adds an existing platform user to an organization by email.
        Business Rules:
        1. Only owner or admin can add members.
        2. The invited email must exist on the platform.
        3. The user cannot already be a member of this organization.
        4. Valid role must be provided.
        """
        role = self.org_repo.get_member_role(org_id, current_user.id)
        if not current_user.is_superadmin and role not in (OrgRole.OWNER, OrgRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners or admins can add members.",
            )

        if request.role not in OrgRole.ALL:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {', '.join(OrgRole.ALL)}",
            )

        # Look up target user
        user_to_add = self.user_repo.get_by_email(request.email)
        if not user_to_add:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No user found with email '{request.email}'. The user must register first.",
            )

        if self.org_repo.is_member(org_id, user_to_add.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"User '{request.email}' is already a member of this organization.",
            )

        member = self.org_repo.add_member(org_id, user_to_add.id, request.role)
        logger.info(f"Added {user_to_add.email} as {request.role} to org {org_id}")
        return MemberResponse.model_validate(member)

    def remove_member(
        self, org_id: str | UUID, user_id: str | UUID, current_user: User
    ) -> dict:
        """
        Removes a member from the organization.
        Business Rules:
        1. Only owner can remove members (or users can remove themselves).
        2. An owner cannot remove themselves if they are the sole owner.
        """
        role = self.org_repo.get_member_role(org_id, current_user.id)
        is_self = str(user_id) == str(current_user.id)

        if not current_user.is_superadmin and role != OrgRole.OWNER and not is_self:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners can remove members.",
            )

        # Check if target is the last owner
        target_role = self.org_repo.get_member_role(org_id, user_id)
        if target_role == OrgRole.OWNER:
            members = self.org_repo.get_members(org_id)
            owners = [m for m in members if m.role == OrgRole.OWNER]
            if len(owners) <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot remove the only owner of an organization.",
                )

        removed = self.org_repo.remove_member(org_id, user_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found in this organization.",
            )

        return {"message": "Member removed successfully."}
