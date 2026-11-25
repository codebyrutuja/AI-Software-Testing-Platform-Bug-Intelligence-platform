"""
app/schemas/organization.py
PURPOSE: Pydantic schemas for Organization and Member API contracts.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserSummary(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str] = None
    model_config = {"from_attributes": True}


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Organization display name")
    description: Optional[str] = Field(None, max_length=1000)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class MemberResponse(BaseModel):
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    joined_at: datetime
    user: Optional[UserSummary] = None
    model_config = {"from_attributes": True}


class AddMemberRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="member", description="Role: owner, admin, member, or viewer")
