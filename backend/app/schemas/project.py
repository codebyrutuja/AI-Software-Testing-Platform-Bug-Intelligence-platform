"""
app/schemas/project.py
PURPOSE: Pydantic schemas for Project API contracts.
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    key: str = Field(..., min_length=2, max_length=10, description="Unique project prefix, e.g. MOB, PAY")
    description: Optional[str] = Field(None, max_length=1000)

    @field_validator("key")
    @classmethod
    def key_must_be_uppercase_letters(cls, v: str) -> str:
        v = v.upper().strip()
        if not re.match(r'^[A-Z]{2,10}$', v):
            raise ValueError("Project key must be 2-10 uppercase letters only (e.g. MOB, PAY, WEB). No digits or symbols.")
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="active or archived")


class ProjectResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    key: str
    description: Optional[str]
    status: str
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}
