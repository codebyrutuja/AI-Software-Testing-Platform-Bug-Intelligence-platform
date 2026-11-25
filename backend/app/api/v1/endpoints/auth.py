"""
app/api/v1/endpoints/auth.py
─────────────────────────────
PURPOSE:
  HTTP endpoints for authentication.
  These are thin — they just validate input, call the service, and return responses.
  NO business logic here (that lives in auth_service.py).
"""

import logging
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - Email must be unique
    - Password min 8 chars, must have uppercase + digit
    - New users start with 'member' role
    """
    service = AuthService(db)
    return service.register(user_data)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login and get JWT tokens",
)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.

    Returns:
    - **access_token**: Use in `Authorization: Bearer <token>` header
    - **refresh_token**: Use to get a new access token when it expires
    - **expires_in**: Seconds until the access token expires
    """
    service = AuthService(db)
    return service.login(login_data)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token using refresh token",
)
def refresh_token(refresh_data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Exchange a valid refresh token for a new access + refresh token pair.
    Use this when the access token expires (HTTP 401) instead of re-logging in.
    """
    service = AuthService(db)
    return service.refresh_tokens(refresh_data)


@router.post(
    "/logout",
    summary="Logout (client-side token invalidation)",
    status_code=status.HTTP_200_OK,
)
def logout(current_user=Depends(get_current_active_user)):
    """
    Logout the current user.

    Note: JWT tokens are stateless — the server cannot invalidate them.
    The client is responsible for deleting the tokens from storage.
    This endpoint confirms the user is authenticated before the client clears tokens.

    Token blacklisting (server-side invalidation) will be added in Phase 9+ if needed.
    """
    logger.info(f"User logged out: {current_user.email}")
    return {"message": "Successfully logged out. Please clear your tokens."}


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current authenticated user profile",
)
def get_me(current_user=Depends(get_current_active_user)):
    """
    Returns the profile of the currently authenticated user.
    Requires a valid Bearer token in the Authorization header.
    """
    return current_user
