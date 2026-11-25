"""
app/schemas/bug.py
──────────────────
PURPOSE: Pydantic schemas for Phase 7 Bug Tracker & Defect Management.
"""
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BugCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: str = Field("medium", description="critical, high, medium, low")
    priority: str = Field("medium", description="critical, high, medium, low")
    environment: Optional[str] = None
    browser_os: Optional[str] = None
    test_case_id: Optional[UUID] = None
    requirement_id: Optional[UUID] = None
    test_run_item_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None


class BugUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    environment: Optional[str] = None
    browser_os: Optional[str] = None
    assigned_to: Optional[UUID] = None


class BugResponse(BaseModel):
    id: UUID
    project_id: UUID
    bug_key: str
    title: str
    description: Optional[str] = None
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    severity: str
    priority: str
    status: str
    environment: Optional[str] = None
    browser_os: Optional[str] = None
    test_run_item_id: Optional[UUID] = None
    test_case_id: Optional[UUID] = None
    tc_key: Optional[str] = None
    tc_title: Optional[str] = None
    requirement_id: Optional[UUID] = None
    requirement_key: Optional[str] = None
    requirement_title: Optional[str] = None
    reported_by: Optional[UUID] = None
    reporter_name: Optional[str] = None
    assigned_to: Optional[UUID] = None
    assignee_name: Optional[str] = None
    reported_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class BugListResponse(BaseModel):
    items: List[BugResponse]
    total: int
    skip: int
    limit: int


class BugStatsResponse(BaseModel):
    total: int
    open: int
    in_progress: int
    resolved: int
    closed: int
    wont_fix: int
    by_severity: Dict[str, int]
