"""
app/api/v1/endpoints/test_runs.py
──────────────────────────────────
PURPOSE:
  REST endpoints for Test Execution Runs & Results (Phase 6).
  7 endpoints covering full CRUD for runs and result submission per item.
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.test_run import (
    RunCreate,
    RunItemResponse,
    RunItemUpdate,
    RunListResponse,
    RunResponse,
    RunUpdate,
)
from app.services.test_run_service import TestRunService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/projects/{project_id}/runs",
    response_model=RunListResponse,
    summary="List all test runs for a project",
)
def list_runs(
    project_id: UUID,
    status: Optional[str] = Query(None, description="planned, in_progress, completed, aborted"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.list_runs(project_id, current_user, status_filter=status, skip=skip, limit=limit)


@router.post(
    "/projects/{project_id}/runs",
    response_model=RunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new test execution run",
)
def create_run(
    project_id: UUID,
    data: RunCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.create_run(project_id, data, current_user)


@router.get(
    "/projects/{project_id}/runs/{run_id}",
    response_model=RunResponse,
    summary="Get test run details with all items and progress stats",
)
def get_run(
    project_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.get_run(project_id, run_id, current_user)


@router.put(
    "/projects/{project_id}/runs/{run_id}",
    response_model=RunResponse,
    summary="Update test run metadata or status",
)
def update_run(
    project_id: UUID,
    run_id: UUID,
    data: RunUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.update_run(project_id, run_id, data, current_user)


@router.delete(
    "/projects/{project_id}/runs/{run_id}",
    summary="Delete a test run and all its result items",
)
def delete_run(
    project_id: UUID,
    run_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.delete_run(project_id, run_id, current_user)


@router.put(
    "/projects/{project_id}/runs/{run_id}/items/{item_id}/result",
    response_model=RunItemResponse,
    summary="Submit Pass / Fail / Blocked / Skipped result for one test item",
)
def submit_item_result(
    project_id: UUID,
    run_id: UUID,
    item_id: UUID,
    data: RunItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = TestRunService(db)
    return service.submit_item_result(project_id, run_id, item_id, data, current_user)
