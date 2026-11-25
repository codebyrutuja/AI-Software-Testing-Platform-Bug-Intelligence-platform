"""
app/api/v1/endpoints/bugs.py
────────────────────────────
PURPOSE:
  REST endpoints for Bug Tracker & Defect Management (Phase 7).
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.bug import (
    BugCreate,
    BugListResponse,
    BugResponse,
    BugStatsResponse,
    BugUpdate,
)
from app.services.bug_service import BugService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/projects/{project_id}/bugs",
    response_model=BugListResponse,
    summary="List all bugs with filters, search and pagination",
)
def list_bugs(
    project_id: UUID,
    status: Optional[str] = Query(None, description="open, in_progress, resolved, closed, wont_fix"),
    severity: Optional[str] = Query(None, description="critical, high, medium, low"),
    priority: Optional[str] = Query(None, description="critical, high, medium, low"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned user ID"),
    search: Optional[str] = Query(None, description="Search title, description, or bug key"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.list_bugs(
        project_id=project_id,
        current_user=current_user,
        status=status,
        severity=severity,
        priority=priority,
        assigned_to=assigned_to,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/projects/{project_id}/bugs",
    response_model=BugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Report a new bug",
)
def create_bug(
    project_id: UUID,
    data: BugCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.create_bug(project_id, data, current_user)


@router.get(
    "/projects/{project_id}/bugs/stats",
    response_model=BugStatsResponse,
    summary="Get bug counts by status and severity for dashboard/overview",
)
def get_bug_stats(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.get_stats(project_id, current_user)


@router.get(
    "/projects/{project_id}/bugs/{bug_id}",
    response_model=BugResponse,
    summary="Get full details of a specific bug",
)
def get_bug(
    project_id: UUID,
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.get_bug(project_id, bug_id, current_user)


@router.put(
    "/projects/{project_id}/bugs/{bug_id}",
    response_model=BugResponse,
    summary="Update bug details, status or assignment",
)
def update_bug(
    project_id: UUID,
    bug_id: UUID,
    data: BugUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.update_bug(project_id, bug_id, data, current_user)


@router.delete(
    "/projects/{project_id}/bugs/{bug_id}",
    summary="Delete a bug",
)
def delete_bug(
    project_id: UUID,
    bug_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.delete_bug(project_id, bug_id, current_user)


@router.post(
    "/projects/{project_id}/runs/{run_id}/items/{item_id}/report-bug",
    response_model=BugResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quick-report a bug from a failed test run item",
)
def quick_report_bug(
    project_id: UUID,
    run_id: UUID,
    item_id: UUID,
    data: BugCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    service = BugService(db)
    return service.quick_report_from_run_item(project_id, run_id, item_id, data, current_user)
