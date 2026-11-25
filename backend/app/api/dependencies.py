"""
app/api/dependencies.py
────────────────────────
PURPOSE:
  Reusable FastAPI dependency functions that are injected into API endpoints.
  Think of these as "middleware helpers" that run before the actual endpoint logic.

WHAT IS DEPENDENCY INJECTION?
  Instead of writing the same authentication check in every endpoint,
  we write it once here and inject it where needed.

  Example:
    @router.get("/projects")
    def list_projects(current_user = Depends(get_current_user)):
        # FastAPI automatically calls get_current_user() and passes the result
        return projects_for(current_user)

DEPENDENCIES HERE:
  1. get_current_user   — Validates JWT, returns the logged-in user
  2. get_current_active_user — Same but also checks user is not deactivated
  3. require_superadmin  — Only allows super admins
"""

import logging
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token

logger = logging.getLogger(__name__)

# HTTPBearer extracts the "Bearer <token>" from the Authorization header
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """
    Validates the JWT token from the Authorization header.
    Returns the User database object if valid.
    Raises HTTP 401 if the token is missing, invalid, or expired.

    Flow:
    1. HTTPBearer extracts the token from the header.
    2. decode_token() validates the signature and expiry.
    3. We look up the user in the database.
    4. Return the user object.
    """
    # Import here to avoid circular imports
    from app.repositories.user_repository import UserRepository

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        logger.warning("Invalid or expired token presented")
        raise credentials_exception

    # Check it's an access token (not a refresh token)
    if payload.get("type") != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = user_repo.get_by_id(user_id)

    if user is None:
        logger.warning(f"Token valid but user {user_id} not found")
        raise credentials_exception

    return user


def get_current_active_user(current_user=Depends(get_current_user)):
    """
    Extends get_current_user to also check the user is active.
    Deactivated users should not be able to perform any actions.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator.",
        )
    return current_user


def require_superadmin(current_user=Depends(get_current_active_user)):
    """
    Restricts access to Super Admins only.
    Use this for platform-level management endpoints.
    """
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required.",
        )
    return current_user


def get_organization_member(
    org_id: UUID,
    current_user=Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    TENANT ISOLATION guard.
    Verifies that the current user belongs to the requested organization.
    Returns the OrganizationMember object if valid.
    Raises HTTP 403 if user is not a member.
    """
    from app.models.organization import OrganizationMember, OrgRole
    from app.repositories.organization_repository import OrganizationRepository

    repo = OrganizationRepository(db)
    member = repo.get_member(org_id, current_user.id)

    if not member:
        if current_user.is_superadmin:
            # Superadmin bypass
            return OrganizationMember(
                organization_id=org_id,
                user_id=current_user.id,
                role=OrgRole.OWNER,
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization.",
        )
    return member

'''Checks: "Is this member an admin or owner?" (Used for inviting members or updating company info).'''
def require_org_admin(
    membership=Depends(get_organization_member),
    current_user=Depends(get_current_active_user),
):
    """
    Restricts access to organization admins and owners (or platform superadmin).
    """
    from app.models.organization import OrgRole

    if current_user.is_superadmin:
        return membership

    if membership.role not in (OrgRole.OWNER, OrgRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin or owner access required.",
        )
    return membership

'''Is this member the owner?" (Used for high-stakes actions like deleting the organization).'''
def require_org_owner(
    membership=Depends(get_organization_member),
    current_user=Depends(get_current_active_user),
):
    """
    Restricts access to organization owners only (or platform superadmin).
    """
    from app.models.organization import OrgRole

    if current_user.is_superadmin:
        return membership

    if membership.role != OrgRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization owner access required.",
        )
    return membership


