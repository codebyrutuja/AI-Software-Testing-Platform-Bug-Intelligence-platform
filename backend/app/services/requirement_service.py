"""
app/services/requirement_service.py
───────────────────────────────────
PURPOSE:
  Business logic for Phase 4 Requirements Management:
  1. Document Upload & Extraction Pipeline
  2. Manual Requirement Creation & Editing
  3. Multi-Tenant Project Scoping & Authorization
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.models.requirement import DocParsingStatus, RequirementDocument
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.requirement_repository import RequirementRepository
from app.schemas.requirement import (
    DocumentUploadResponse,
    RequirementCreate,
    RequirementDocumentResponse,
    RequirementListResponse,
    RequirementResponse,
    RequirementUpdate,
)
from app.services.parser_service import DocumentParserService

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


class RequirementService:
    def __init__(self, db: Session):
        self.db = db
        self.req_repo = RequirementRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)

    def _verify_project_access(self, project_id: str | UUID, current_user: User) -> Project:
        """
        Enforces tenant isolation:
        Verifies project exists and user is a member of its organization.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project or project.status == ProjectStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        if not current_user.is_superadmin and not self.org_repo.is_member(
            project.organization_id, current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project.",
            )

        return project

    # ── Upload & Ingestion ──────────────────────────────────────────────────────

    def upload_and_parse_document(
        self, project_id: str | UUID, file: UploadFile, current_user: User
    ) -> DocumentUploadResponse:
        """
        Processes an uploaded PRD document (.md, .txt, .pdf):
        1. Validates format and size.
        2. Extracts raw text.
        3. Parses into structured user stories and acceptance criteria.
        4. Saves document record and creates structured requirements.
        """
        project = self._verify_project_access(project_id, current_user)

        # Validate filename
        filename = file.filename or "uploaded_document"
        lower_name = filename.lower()
        if not any(lower_name.endswith(ext) for ext in (".md", ".txt", ".pdf")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file format. Only .md, .txt, and .pdf files are supported.",
            )

        # Read file contents synchronously and check size
        if hasattr(file, "file") and hasattr(file.file, "read"):
            file_bytes = file.file.read()
        elif hasattr(file, "read"):
            file_bytes = file.read()
        else:
            file_bytes = b""

        file_size = len(file_bytes)
        if file_size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The uploaded file is empty.",
            )
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds maximum allowed limit of 10 MB.",
            )

        # Extract text
        try:
            raw_text, file_type = DocumentParserService.extract_text(file_bytes, filename)
        except Exception as e:
            logger.warning(f"File text extraction failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to process document: {str(e)}",
            )

        # Save document record (status=pending)
        doc = self.req_repo.create_document(
            project_id=project.id,
            uploaded_by=current_user.id,
            filename=filename,
            file_type=file_type,
            file_size_bytes=file_size,
            raw_content=raw_text,
            parsing_status=DocParsingStatus.PENDING,
        )

        # Parse requirements
        try:
            parsed_items = DocumentParserService.parse_requirements(raw_text)
            created_reqs: List[RequirementResponse] = []

            for item in parsed_items:
                req_key = self.req_repo.get_next_req_key(project.id, project.key)
                req = self.req_repo.create_requirement(
                    project_id=project.id,
                    req_key=req_key,
                    title=item["title"],
                    description=item.get("description"),
                    category=item.get("category", "functional"),
                    priority=item.get("priority", "medium"),
                    status="draft",
                    created_by=current_user.id,
                    document_id=doc.id,
                    criteria_list=item.get("acceptance_criteria", []),
                )
                created_reqs.append(RequirementResponse.model_validate(req))

            self.req_repo.update_document_status(doc.id, DocParsingStatus.PARSED)
            logger.info(
                f"Successfully parsed {len(created_reqs)} requirements from '{filename}' for project {project.key}"
            )

            doc_response = RequirementDocumentResponse.model_validate(doc)
            doc_response.parsing_status = DocParsingStatus.PARSED
            doc_response.requirements_count = len(created_reqs)

            return DocumentUploadResponse(
                document=doc_response,
                extracted_count=len(created_reqs),
                requirements=created_reqs,
            )

        except Exception as e:
            logger.error(f"Failed to parse document items: {str(e)}")
            self.req_repo.update_document_status(doc.id, DocParsingStatus.FAILED)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while parsing requirements: {str(e)}",
            )

    # ── CRUD Operations ─────────────────────────────────────────────────────────

    def create_requirement(
        self, project_id: str | UUID, data: RequirementCreate, current_user: User
    ) -> RequirementResponse:
        """
        Manually creates a new requirement with sequential key and criteria.
        """
        project = self._verify_project_access(project_id, current_user)
        req_key = self.req_repo.get_next_req_key(project.id, project.key)

        req = self.req_repo.create_requirement(
            project_id=project.id,
            req_key=req_key,
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            status=data.status,
            created_by=current_user.id,
            criteria_list=data.acceptance_criteria,
        )
        return RequirementResponse.model_validate(req)

    def list_requirements(
        self,
        project_id: str | UUID,
        current_user: User,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> RequirementListResponse:
        """
        Lists paginated requirements with search and filters.
        """
        project = self._verify_project_access(project_id, current_user)

        items = self.req_repo.list_requirements(
            project_id=project.id,
            category=category,
            priority=priority,
            status=status,
            search=search,
            skip=skip,
            limit=limit,
        )
        total = self.req_repo.count_requirements(
            project_id=project.id,
            category=category,
            priority=priority,
            status=status,
            search=search,
        )

        return RequirementListResponse(
            items=[RequirementResponse.model_validate(r) for r in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_requirement(
        self, project_id: str | UUID, req_id: str | UUID, current_user: User
    ) -> RequirementResponse:
        """
        Fetches detailed requirement specifications and acceptance criteria.
        """
        self._verify_project_access(project_id, current_user)

        req = self.req_repo.get_requirement_by_id(req_id, project_id)
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found in this project.",
            )

        return RequirementResponse.model_validate(req)

    def update_requirement(
        self,
        project_id: str | UUID,
        req_id: str | UUID,
        data: RequirementUpdate,
        current_user: User,
    ) -> RequirementResponse:
        """
        Updates requirement fields and/or acceptance criteria list.
        """
        self._verify_project_access(project_id, current_user)

        existing = self.req_repo.get_requirement_by_id(req_id, project_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found in this project.",
            )

        updated = self.req_repo.update_requirement(
            req_id=req_id,
            title=data.title,
            description=data.description,
            category=data.category,
            priority=data.priority,
            status=data.status,
            criteria_list=data.acceptance_criteria,
        )
        return RequirementResponse.model_validate(updated)

    def delete_requirement(
        self, project_id: str | UUID, req_id: str | UUID, current_user: User
    ) -> dict:
        """
        Deletes a requirement and cascades its acceptance criteria.
        """
        self._verify_project_access(project_id, current_user)

        existing = self.req_repo.get_requirement_by_id(req_id, project_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Requirement not found in this project.",
            )

        self.req_repo.delete_requirement(req_id)
        return {"message": "Requirement deleted successfully."}

    def list_documents(
        self,
        project_id: str | UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 50,
    ) -> List[RequirementDocumentResponse]:
        """
        Lists documents uploaded to this project.
        """
        project = self._verify_project_access(project_id, current_user)
        docs = self.req_repo.list_documents(project.id, skip=skip, limit=limit)
        return [RequirementDocumentResponse.model_validate(d) for d in docs]
