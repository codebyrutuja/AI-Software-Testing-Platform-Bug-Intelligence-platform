"""
app/api/v1/endpoints/projects.py
────────────────────────────────
PURPOSE:
  REST endpoints for Software Projects inside Organizations.
"""
import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_current_active_user,
    get_organization_member,
    require_org_admin,
)
from app.core.database import get_db
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project_service import ProjectService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/organizations/{org_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new software project inside an organization",
)
def create_project(
    org_id: UUID,
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(get_organization_member),
):
    """
    Creates a new project in the specified organization.
    The project key must be 2-10 uppercase letters and unique within the organization.
    """
    service = ProjectService(db)
    return service.create_project(org_id, data, current_user)


@router.get(
    "/organizations/{org_id}/projects",
    response_model=List[ProjectResponse],
    summary="List all active projects in an organization",
)
def list_projects(
    org_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    _membership=Depends(get_organization_member),
):
    """
    Returns a paginated list of active projects in this organization.
    """
    service = ProjectService(db)
    return service.list_projects(org_id, current_user, skip=skip, limit=limit)


@router.get(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns project details. Enforces tenant isolation — user must belong to the organization.
    """
    service = ProjectService(db)
    return service.get_project(project_id, current_user)


@router.patch(
    "/projects/{project_id}",
    response_model=ProjectResponse,
    summary="Update project details",
)
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Updates project name, description, or status.
    Requires owner or admin role in the parent organization.
    """
    service = ProjectService(db)
    return service.update_project(project_id, data, current_user)


@router.delete(
    "/projects/{project_id}",
    summary="Archive (soft delete) a project",
)
def archive_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Archives a project.
    Requires owner or admin role in the parent organization.
    """
    service = ProjectService(db)
    return service.archive_project(project_id, current_user)
