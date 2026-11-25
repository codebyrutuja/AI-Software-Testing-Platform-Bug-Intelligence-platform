"""
app/services/project_service.py
───────────────────────────────
PURPOSE:
  Business logic for Software Projects within Organizations.
  Enforces multi-tenancy isolation and unique key constraints.
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.organization import OrgRole
from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

logger = logging.getLogger(__name__)


class ProjectService:
    def __init__(self, db: Session):
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)

    def create_project(
        self, org_id: str | UUID, data: ProjectCreate, current_user: User
    ) -> ProjectResponse:
        """
        Creates a new project in the specified organization.
        Business Rules:
        1. Current user must be a member of the organization (or superadmin).
        2. Project key must be unique within this organization.
        """
        org = self.org_repo.get_by_id(org_id)
        if not org or not org.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        if not current_user.is_superadmin and not self.org_repo.is_member(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )

        key_upper = data.key.upper().strip()
        if self.project_repo.key_exists_in_org(org_id, key_upper):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A project with key '{key_upper}' already exists in this organization.",
            )

        project = self.project_repo.create(org_id, data, current_user.id)
        logger.info(
            f"User {current_user.email} created project '{project.name}' ({project.key}) in org {org_id}"
        )
        return ProjectResponse.model_validate(project)

    def list_projects(
        self,
        org_id: str | UUID,
        current_user: User,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ProjectResponse]:
        """
        Lists all active projects in the organization.
        Requires organization membership.
        """
        if not current_user.is_superadmin and not self.org_repo.is_member(org_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization.",
            )

        projects = self.project_repo.get_by_org(org_id, skip=skip, limit=limit)
        return [ProjectResponse.model_validate(p) for p in projects]

    def get_project(
        self, project_id: str | UUID, current_user: User
    ) -> ProjectResponse:
        """
        Retrieves a single project's details.
        Enforces tenant isolation: user must belong to the project's organization.
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

        return ProjectResponse.model_validate(project)

    def update_project(
        self, project_id: str | UUID, data: ProjectUpdate, current_user: User
    ) -> ProjectResponse:
        """
        Updates project details.
        Requires owner or admin role in the organization.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project or project.status == ProjectStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        role = self.org_repo.get_member_role(project.organization_id, current_user.id)
        if not current_user.is_superadmin and role not in (OrgRole.OWNER, OrgRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners or admins can update project details.",
            )

        updated = self.project_repo.update(project_id, data)
        return ProjectResponse.model_validate(updated)

    def archive_project(
        self, project_id: str | UUID, current_user: User
    ) -> dict:
        """
        Soft deletes (archives) a project.
        Requires owner or admin role in the organization.
        """
        project = self.project_repo.get_by_id(project_id)
        if not project or project.status == ProjectStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found.",
            )

        role = self.org_repo.get_member_role(project.organization_id, current_user.id)
        if not current_user.is_superadmin and role not in (OrgRole.OWNER, OrgRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners or admins can archive projects.",
            )

        self.project_repo.archive(project_id)
        logger.info(f"Archived project {project.key} ({project.id})")
        return {"message": "Project archived successfully."}
