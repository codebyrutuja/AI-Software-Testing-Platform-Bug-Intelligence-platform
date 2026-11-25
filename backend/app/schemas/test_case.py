"""
app/schemas/test_case.py
────────────────────────
PURPOSE: Pydantic schemas for Phase 5 Test Cases & Test Suites contracts.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ── Test Steps Schemas ────────────────────────────────────────────────────────

class TestStepBase(BaseModel):
    __test__ = False
    step_number: int = Field(1, ge=1)
    action: str = Field(..., min_length=1)
    test_data: Optional[str] = None
    expected_result: str = Field(..., min_length=1)


class TestStepCreate(TestStepBase):
    pass


class TestStepUpdate(BaseModel):
    id: Optional[UUID] = None
    step_number: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    test_data: Optional[str] = None
    expected_result: str = Field(..., min_length=1)


class TestStepResponse(TestStepBase):
    id: UUID
    test_case_id: UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Test Suites Schemas ───────────────────────────────────────────────────────

class TestSuiteCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    parent_suite_id: Optional[UUID] = None


class TestSuiteUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    parent_suite_id: Optional[UUID] = None


class TestSuiteResponse(BaseModel):
    id: UUID
    project_id: UUID
    parent_suite_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    created_at: datetime
    case_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# ── Test Cases Schemas ────────────────────────────────────────────────────────

class TestCaseCreate(BaseModel):
    __test__ = False
    title: str = Field(..., min_length=2, max_length=255)
    suite_id: Optional[UUID] = None
    requirement_id: Optional[UUID] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    test_type: str = Field("manual", description="manual, automated, regression, smoke, sanity")
    priority: str = Field("medium", description="low, medium, high, critical")
    status: str = Field("active", description="draft, active, deprecated")
    estimated_duration_minutes: int = Field(5, ge=1, le=1440)
    steps: Optional[List[TestStepCreate]] = Field(default_factory=list)


class TestCaseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    suite_id: Optional[UUID] = None
    requirement_id: Optional[UUID] = None
    description: Optional[str] = None
    preconditions: Optional[str] = None
    test_type: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, ge=1, le=1440)
    steps: Optional[List[TestStepCreate]] = None


class TestCaseResponse(BaseModel):
    id: UUID
    project_id: UUID
    suite_id: Optional[UUID] = None
    suite_name: Optional[str] = None
    requirement_id: Optional[UUID] = None
    requirement_key: Optional[str] = None
    requirement_title: Optional[str] = None
    tc_key: str
    title: str
    description: Optional[str] = None
    preconditions: Optional[str] = None
    test_type: str
    priority: str
    status: str
    estimated_duration_minutes: int
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime
    steps: List[TestStepResponse] = []
    model_config = ConfigDict(from_attributes=True)


class TestCaseListResponse(BaseModel):
    items: List[TestCaseResponse]
    total: int
    skip: int
    limit: int

