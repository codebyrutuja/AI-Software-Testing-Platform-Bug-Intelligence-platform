"""
app/schemas/test_run.py
────────────────────────
PURPOSE: Pydantic schemas for Phase 6 Test Execution Runs & Results contracts.

NOTE: Classes starting with "Test" have __test__ = False to prevent pytest
      from trying to collect them as test classes.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# ── Test Run Item Schemas ─────────────────────────────────────────────────────

class RunItemUpdate(BaseModel):
    """Payload sent when a tester records the result of one test case."""
    result: str = Field(..., description="passed, failed, blocked, skipped")
    failure_notes: Optional[str] = Field(None, description="Failure details — required when result=failed")
    actual_duration_minutes: Optional[int] = Field(None, ge=1, le=1440)


class RunItemResponse(BaseModel):
    """Full response for a single test-run item (one test case inside a run)."""
    __test__ = False

    id: UUID
    test_run_id: UUID
    test_case_id: Optional[UUID] = None
    tc_key: Optional[str] = None          # e.g. ECOM-TC-01
    tc_title: Optional[str] = None        # human-readable test case title
    result: str
    failure_notes: Optional[str] = None
    actual_duration_minutes: Optional[int] = None
    executed_by: Optional[UUID] = None
    executed_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── Test Run Schemas ──────────────────────────────────────────────────────────

class RunCreate(BaseModel):
    """Payload to create a new test run."""
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    environment: str = Field("staging", description="local, staging, qa, production")
    test_case_ids: List[UUID] = Field(..., min_length=1, description="Test cases to include in this run")


class RunUpdate(BaseModel):
    """Payload to update run metadata or status."""
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    status: Optional[str] = Field(None, description="planned, in_progress, completed, aborted")
    environment: Optional[str] = Field(None, description="local, staging, qa, production")


class RunResponse(BaseModel):
    """Full run response with progress statistics."""
    __test__ = False

    id: UUID
    project_id: UUID
    run_key: str
    name: str
    description: Optional[str] = None
    status: str
    environment: str
    created_by: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Progress stats (computed at response time)
    total_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    blocked_count: int = 0
    skipped_count: int = 0
    not_run_count: int = 0

    items: List[RunItemResponse] = []
    model_config = ConfigDict(from_attributes=True)


class RunListResponse(BaseModel):
    """Paginated list of test runs."""
    items: List[RunResponse]
    total: int
    skip: int
    limit: int
