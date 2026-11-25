"""
app/api/v1/endpoints/organizations.py
──────────────────────────────────────
PURPOSE:
  REST endpoints for Organization workspaces and member management.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_active_user,
    get_organization_member,
    require_org_admin,
    require_org_owner,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.organization import (
    AddMemberRequest,
    MemberResponse,
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_service import OrganizationService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new organization workspace",
)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Creates a new organization.
    The authenticated user automatically becomes the organization owner.
    """
    service = OrganizationService(db)
    return service.create_organization(data, current_user)


@router.get(
    "/",
    response_model=List[OrganizationResponse],
    summary="List all organizations the user belongs to",
)
def list_my_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns all organizations where the current user is a member.
    """
    service = OrganizationService(db)
    return service.get_my_organizations(current_user)


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get organization details",
)
def get_organization(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(get_organization_member),
):
    """
    Returns organization profile. Requires user to be a member of the organization.
    """
    service = OrganizationService(db)
    return service.get_organization(org_id, current_user)


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Update organization details",
)
def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(require_org_admin),
):
    """
    Updates organization name or description. Requires owner or admin role.
    """
    service = OrganizationService(db)
    return service.update_organization(org_id, data, current_user)


@router.get(
    "/{org_id}/members",
    response_model=List[MemberResponse],
    summary="List organization members",
)
def list_members(
    org_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(get_organization_member),
):
    """
    Lists all members and their roles in this organization. Requires membership.
    """
    service = OrganizationService(db)
    return service.get_members(org_id, current_user)


@router.post(
    "/{org_id}/members",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a member to the organization",
)
def add_member(
    org_id: UUID,
    request: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(require_org_admin),
):
    """
    Invites/adds an existing user to this organization by email.
    Requires owner or admin role.
    """
    service = OrganizationService(db)
    return service.add_member(org_id, request, current_user)


@router.delete(
    "/{org_id}/members/{user_id}",
    summary="Remove a member from the organization",
)
def remove_member(
    org_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(get_organization_member),
):
    """
    Removes a member from the organization.
    Requires owner role, or member removing themselves.
    """
    service = OrganizationService(db)
    return service.remove_member(org_id, user_id, current_user)
