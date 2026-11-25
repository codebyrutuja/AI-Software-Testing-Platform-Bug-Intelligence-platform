"""
app/schemas/requirement.py
──────────────────────────
PURPOSE: Pydantic schemas for Phase 4 Requirements Management contracts.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class AcceptanceCriteriaBase(BaseModel):
    criteria: str = Field(..., min_length=1, max_length=2000)
    order_index: int = Field(0, ge=0)


class AcceptanceCriteriaCreate(AcceptanceCriteriaBase):
    pass


class AcceptanceCriteriaUpdate(BaseModel):
    id: Optional[UUID] = None
    criteria: str = Field(..., min_length=1, max_length=2000)
    order_index: int = Field(0, ge=0)


class AcceptanceCriteriaResponse(AcceptanceCriteriaBase):
    id: UUID
    requirement_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class RequirementCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    category: str = Field("functional", description="functional, non_functional, security, ui_ux, performance")
    priority: str = Field("medium", description="low, medium, high, critical")
    status: str = Field("draft", description="draft, approved, deprecated")
    acceptance_criteria: Optional[List[str]] = Field(default_factory=list, description="List of criteria descriptions")


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    acceptance_criteria: Optional[List[str]] = None


class RequirementResponse(BaseModel):
    id: UUID
    project_id: UUID
    document_id: Optional[UUID] = None
    req_key: str
    title: str
    description: Optional[str] = None
    category: str
    priority: str
    status: str
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    acceptance_criteria: List[AcceptanceCriteriaResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RequirementListResponse(BaseModel):
    items: List[RequirementResponse]
    total: int
    skip: int
    limit: int


class RequirementDocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    uploaded_by: Optional[UUID] = None
    filename: str
    file_type: str
    file_size_bytes: int
    parsing_status: str
    created_at: datetime
    requirements_count: Optional[int] = 0
    model_config = ConfigDict(from_attributes=True)


class DocumentUploadResponse(BaseModel):
    document: RequirementDocumentResponse
    extracted_count: int
    requirements: List[RequirementResponse]
