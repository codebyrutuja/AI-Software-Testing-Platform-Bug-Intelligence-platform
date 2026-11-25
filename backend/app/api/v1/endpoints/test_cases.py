"""
app/api/v1/endpoints/test_cases.py
──────────────────────────────────
PURPOSE:
  REST endpoints for Test Suites and Test Cases Management (Phase 5).
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdate,
    TestSuiteCreate,
    TestSuiteResponse,
    TestSuiteUpdate,
)
from app.services.test_case_service import TestCaseService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Test Suites Endpoints ─────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/suites",
    response_model=List[TestSuiteResponse],
    summary="List all test suites for a project",
)
def list_suites(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.list_suites(project_id, current_user)


@router.post(
    "/projects/{project_id}/suites",
    response_model=TestSuiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test suite folder",
)
def create_suite(
    project_id: UUID,
    data: TestSuiteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.create_suite(project_id, data, current_user)


@router.put(
    "/projects/{project_id}/suites/{suite_id}",
    response_model=TestSuiteResponse,
    summary="Update test suite details",
)
def update_suite(
    project_id: UUID,
    suite_id: UUID,
    data: TestSuiteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.update_suite(project_id, suite_id, data, current_user)


@router.delete(
    "/projects/{project_id}/suites/{suite_id}",
    summary="Delete a test suite",
)
def delete_suite(
    project_id: UUID,
    suite_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.delete_suite(project_id, suite_id, current_user)


# ── Test Cases Endpoints ──────────────────────────────────────────────────────

@router.get(
    "/projects/{project_id}/test-cases",
    response_model=TestCaseListResponse,
    summary="List test cases with filters, search, and pagination",
)
def list_test_cases(
    project_id: UUID,
    suite_id: Optional[UUID] = Query(None, description="Filter by test suite folder"),
    requirement_id: Optional[UUID] = Query(None, description="Filter by linked requirement"),
    test_type: Optional[str] = Query(None, description="manual, automated, regression, smoke, sanity"),
    priority: Optional[str] = Query(None, description="low, medium, high, critical"),
    status: Optional[str] = Query(None, description="draft, active, deprecated"),
    search: Optional[str] = Query(None, description="Search by title, description, or key"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.list_cases(
        project_id=project_id,
        current_user=current_user,
        suite_id=suite_id,
        requirement_id=requirement_id,
        test_type=test_type,
        priority=priority,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/test-cases",
    response_model=TestCaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test case with itemized steps",
)
def create_test_case(
    project_id: UUID,
    data: TestCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.create_case(project_id, data, current_user)


@router.get(
    "/projects/{project_id}/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Get detailed test case with all steps and requirement info",
)
def get_test_case(
    project_id: UUID,
    test_case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.get_case(project_id, test_case_id, current_user)


@router.put(
    "/projects/{project_id}/test-cases/{test_case_id}",
    response_model=TestCaseResponse,
    summary="Update test case details and step instructions",
)
def update_test_case(
    project_id: UUID,
    test_case_id: UUID,
    data: TestCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.update_case(project_id, test_case_id, data, current_user)


@router.delete(
    "/projects/{project_id}/test-cases/{test_case_id}",
    summary="Delete a test case and cascade its steps",
)
def delete_test_case(
    project_id: UUID,
    test_case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestCaseService(db)
    return service.delete_case(project_id, test_case_id, current_user)
