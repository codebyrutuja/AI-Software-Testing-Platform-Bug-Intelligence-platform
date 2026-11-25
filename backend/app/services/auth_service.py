"""
app/services/auth_service.py
──────────────────────────────
PURPOSE:
  Business logic for authentication.
  The service layer sits between the API endpoints and the repository.

RESPONSIBILITY SPLIT:
  API endpoint  → HTTP concerns (request/response, status codes)
  Auth Service  → Business logic (login rules, token generation, validation)
  Repository    → Database queries (pure data access)

WHY A SERVICE LAYER?
  Keeps business logic out of both the API layer and the database layer.
  Makes logic reusable across multiple endpoints.
  Makes unit testing straightforward — no HTTP or DB needed.
"""

import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenResponse
from app.schemas.user import ChangePasswordRequest, UserCreate, UserResponse

logger = logging.getLogger(__name__)


class AuthService:
    """
    Handles all authentication business logic.
    Instantiated per-request with a fresh DB session.
    """

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    # ── Registration ──────────────────────────────────────────────────────────────

    def register(self, user_data: UserCreate) -> UserResponse:
        """
        Register a new user account.

        Business rules:
        1. Email must not already be registered
        2. Password is hashed by the repository before storage
        3. New users always start as 'member' role (least privilege)
        """
        # Check for duplicate email
        if self.user_repo.exists_by_email(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"An account with email '{user_data.email}' already exists.",
            )

        user = self.user_repo.create(user_data)
        logger.info(f"New user registered: {user.email}")
        return UserResponse.model_validate(user)

    # ── Login ─────────────────────────────────────────────────────────────────────

    def login(self, login_data: LoginRequest) -> TokenResponse:
        """
        Authenticate a user and issue JWT tokens.

        Security notes:
        - We always check BOTH email existence AND password before returning an error.
          This prevents timing-based user enumeration attacks.
        - We use a generic error message ("Invalid credentials") — not "user not found"
          or "wrong password" separately. This prevents leaking which emails are registered.
        - On success, update last_login_at for audit purposes.
        """
        # Generic error returned for BOTH "user not found" and "wrong password"
        # Prevents user enumeration: attacker can't tell if email exists
        invalid_credentials_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Step 1: Look up user by email
        user = self.user_repo.get_by_email(login_data.email)
        if not user:
            # Still run verify_password with a dummy hash to prevent timing attacks
            verify_password(login_data.password, "$2b$12$dummy_hash_to_prevent_timing")
            raise invalid_credentials_error

        # Step 2: Verify the password against the stored bcrypt hash
        if not verify_password(login_data.password, user.hashed_password):
            raise invalid_credentials_error

        # Step 3: Check the account is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Contact your administrator.",
            )

        # Step 4: Generate JWT tokens
        token_data = {"sub": str(user.id)}

        access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        refresh_token = create_refresh_token(data=token_data)

        # Step 5: Record the login timestamp
        self.user_repo.update_last_login(user.id)

        logger.info(f"User logged in: {user.email}")

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # Convert to seconds
        )

    # ── Token Refresh ─────────────────────────────────────────────────────────────

    def refresh_tokens(self, refresh_data: RefreshTokenRequest) -> TokenResponse:
        """
        Issue a new pair of tokens using a valid refresh token.

        Why refresh tokens?
          Access tokens expire quickly (30 min) for security.
          Refresh tokens allow getting a new access token without re-logging in.
          If a refresh token is stolen, it can be invalidated server-side (Phase 9+).
        """
        invalid_token_error = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

        # Decode and validate the refresh token
        payload = decode_token(refresh_data.refresh_token)
        if not payload:
            raise invalid_token_error

        # Confirm it's specifically a refresh token (not an access token being misused)
        if payload.get("type") != "refresh":
            raise invalid_token_error

        user_id = payload.get("sub")
        if not user_id:
            raise invalid_token_error

        # Confirm the user still exists and is active
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise invalid_token_error

        # Issue fresh tokens
        token_data = {"sub": str(user.id)}
        new_access_token = create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        )
        new_refresh_token = create_refresh_token(data=token_data)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Change Password ───────────────────────────────────────────────────────────

    def change_password(self, user_id: str, request: ChangePasswordRequest) -> dict:
        """
        Allow a logged-in user to change their own password.
        Requires the current password for confirmation (prevents session hijacking).
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Verify they know the current password
        if not verify_password(request.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )

        # Prevent reusing the same password
        if verify_password(request.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must be different from the current password.",
            )

        new_hash = hash_password(request.new_password)
        self.user_repo.update_password(user_id, new_hash)
        logger.info(f"Password changed for user: {user.email}")

        return {"message": "Password changed successfully."}
