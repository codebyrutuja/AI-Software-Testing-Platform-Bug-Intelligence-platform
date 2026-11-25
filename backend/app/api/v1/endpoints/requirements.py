"""
app/api/v1/endpoints/requirements.py
────────────────────────────────────
PURPOSE:
  REST endpoints for Requirements Management and Document Ingestion (Phase 4).
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.requirement import (
    DocumentUploadResponse,
    RequirementCreate,
    RequirementDocumentResponse,
    RequirementListResponse,
    RequirementResponse,
    RequirementUpdate,
)
from app.services.requirement_service import RequirementService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/projects/{project_id}/requirements/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and parse a PRD document (.md, .txt, .pdf)",
)
async def upload_document(
    project_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Uploads a specification or PRD document, extracts text,
    parses requirements/acceptance criteria, and saves them with sequential project keys.
    """
    service = RequirementService(db)
    return await service.upload_and_parse_document(project_id, file, current_user)


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a new requirement",
)
def create_requirement(
    project_id: UUID,
    data: RequirementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Creates a new requirement manually for the specified project.
    """
    service = RequirementService(db)
    return service.create_requirement(project_id, data, current_user)


@router.get(
    "/projects/{project_id}/requirements",
    response_model=RequirementListResponse,
    summary="List requirements for a project with optional filters and pagination",
)
def list_requirements(
    project_id: UUID,
    category: Optional[str] = Query(None, description="functional, non_functional, security, ui_ux, performance"),
    priority: Optional[str] = Query(None, description="low, medium, high, critical"),
    status: Optional[str] = Query(None, description="draft, approved, deprecated"),
    search: Optional[str] = Query(None, description="Search by title, description, or key"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns a paginated list of requirements for the project.
    """
    service = RequirementService(db)
    return service.list_requirements(
        project_id=project_id,
        current_user=current_user,
        category=category,
        priority=priority,
        status=status,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/projects/{project_id}/requirements/{requirement_id}",
    response_model=RequirementResponse,
    summary="Get detailed requirement specifications and acceptance criteria",
)
def get_requirement(
    project_id: UUID,
    requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Retrieves full requirement details including its acceptance criteria.
    """
    service = RequirementService(db)
    return service.get_requirement(project_id, requirement_id, current_user)


@router.put(
    "/projects/{project_id}/requirements/{requirement_id}",
    response_model=RequirementResponse,
    summary="Update requirement details and acceptance criteria",
)
def update_requirement(
    project_id: UUID,
    requirement_id: UUID,
    data: RequirementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Updates a requirement's title, description, category, priority, status, and/or criteria.
    """
    service = RequirementService(db)
    return service.update_requirement(project_id, requirement_id, data, current_user)


@router.delete(
    "/projects/{project_id}/requirements/{requirement_id}",
    summary="Delete a requirement",
)
def delete_requirement(
    project_id: UUID,
    requirement_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Deletes a requirement and cascades its acceptance criteria.
    """
    service = RequirementService(db)
    return service.delete_requirement(project_id, requirement_id, current_user)


@router.get(
    "/projects/{project_id}/documents",
    response_model=List[RequirementDocumentResponse],
    summary="List uploaded specification documents for a project",
)
def list_documents(
    project_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns all uploaded documents and their parsing status for the project.
    """
    service = RequirementService(db)
    return service.list_documents(project_id, current_user, skip=skip, limit=limit)
