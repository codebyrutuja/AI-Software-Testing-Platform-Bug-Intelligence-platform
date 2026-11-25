"""
app/api/v1/endpoints/users.py
──────────────────────────────
PURPOSE:
  HTTP endpoints for user management.
  Superadmin-only endpoints for platform administration.
  Also includes self-service endpoints (profile update, change password).
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user, require_superadmin
from app.core.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.user import ChangePasswordRequest, UserResponse, UserUpdate
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/",
    response_model=List[UserResponse],
    summary="List all users (superadmin only)",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _=Depends(require_superadmin),     # Enforces superadmin access
):
    """
    Returns a paginated list of all registered users.
    Only accessible by platform superadmins.
    """
    repo = UserRepository(db)
    return repo.get_all(skip=skip, limit=limit)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get a user by ID",
)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Fetch a user's profile by their UUID.
    - Any active user can view their own profile.
    - Superadmin can view any user's profile.
    """
    repo = UserRepository(db)
    user = repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found.",
        )

    # Non-superadmins can only view their own profile
    if not current_user.is_superadmin and str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile.",
        )

    return user


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile",
)
def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Update a user's profile (full_name, email).
    Users can only update their own profile unless they are a superadmin.
    """
    if not current_user.is_superadmin and str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile.",
        )

    repo = UserRepository(db)

    # Check new email isn't already taken by another user
    if update_data.email:
        existing = repo.get_by_email(update_data.email)
        if existing and str(existing.id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already registered to another account.",
            )

    updated = repo.update(user_id, update_data)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found.",
        )

    return updated


@router.post(
    "/{user_id}/change-password",
    summary="Change user password",
    status_code=status.HTTP_200_OK,
)
def change_password(
    user_id: UUID,
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_active_user),
):
    """
    Change a user's password.
    Requires the current password for verification.
    Users can only change their own password.
    """
    if str(current_user.id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only change your own password.",
        )

    service = AuthService(db)
    return service.change_password(str(user_id), request)


@router.delete(
    "/{user_id}",
    summary="Deactivate a user (superadmin only)",
    status_code=status.HTTP_200_OK,
)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_superadmin),
):
    """
    Soft-deactivate a user (sets is_active=False).
    Does NOT delete the user — data is preserved for audit purposes.
    Only superadmins can deactivate users.
    """
    # Prevent superadmin from deactivating themselves
    if str(current_user.id) == str(user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account.",
        )

    repo = UserRepository(db)
    success = repo.deactivate(user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id '{user_id}' not found.",
        )

    return {"message": f"User '{user_id}' has been deactivated."}
