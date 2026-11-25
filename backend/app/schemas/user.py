"""
app/schemas/user.py
────────────────────
PURPOSE:
  Pydantic schemas for User data validation.
  These define what data the API accepts (request) and returns (response).

WHY SEPARATE FROM THE MODEL?
  The SQLAlchemy model (models/user.py) defines the DATABASE structure.
  Pydantic schemas define the API's INPUT/OUTPUT contract.
  They are intentionally different:
    - API input (UserCreate) has a plain `password` field
    - Database model (User) has `hashed_password` — never expose the hash
    - API output (UserResponse) omits sensitive fields entirely
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Base Schema ──────────────────────────────────────────────────────────────────
# Shared fields reused by Create/Update/Response schemas
class UserBase(BaseModel):
    email: EmailStr                          # Validates email format automatically
    full_name: Optional[str] = None         # Optional display name


# ── Create Schema (Registration Input) ──────────────────────────────────────────
# Used by: POST /auth/register
# Has `password` — the service will hash it before saving
class UserCreate(UserBase):
    password: str = Field(
        ...,                # Required field (... means no default)
        min_length=8,       # Enforce minimum length at API layer
        description="Must be at least 8 characters",
    )

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Enforce basic password strength rules."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


# ── Update Schema (Profile Update Input) ────────────────────────────────────────
# Used by: PATCH /users/{id}
# All fields optional — only send what you want to change
class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None


# ── Response Schema (What the API returns) ──────────────────────────────────────
# Used as the return type for all user-related endpoints.
# NEVER includes hashed_password — that stays in the database only.
class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str]
    role: str
    is_active: bool
    is_superadmin: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    # `from_attributes=True` allows Pydantic to read from SQLAlchemy ORM objects.
    # Without this, Pydantic only reads from plain dicts.
    model_config = {"from_attributes": True}


# ── Change Password Schema ───────────────────────────────────────────────────────
# Used by: POST /users/{id}/change-password
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def new_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("New password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("New password must contain at least one digit")
        return v
