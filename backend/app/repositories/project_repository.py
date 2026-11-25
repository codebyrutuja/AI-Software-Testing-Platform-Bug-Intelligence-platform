"""
app/repositories/project_repository.py
PURPOSE: All database queries for the Project table.
"""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.schemas.project import ProjectCreate, ProjectUpdate

logger = logging.getLogger(__name__)


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Read Operations ─────────────────────────────────────────────────────────

    def get_by_id(self, project_id: str | UUID) -> Optional[Project]:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        return self.db.query(Project).filter(Project.id == p_val).first()

    def get_by_org(self, org_id: str | UUID, skip: int = 0, limit: int = 100) -> List[Project]:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        return (
            self.db.query(Project)
            .filter(Project.organization_id == o_val)
            .filter(Project.status == ProjectStatus.ACTIVE)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def key_exists_in_org(self, org_id: str | UUID, key: str) -> bool:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        return (
            self.db.query(Project)
            .filter(
                Project.organization_id == o_val,
                Project.key == key.upper(),
            )
            .first()
        ) is not None

    # ── Write Operations ─────────────────────────────────────────────────────────

    def create(self, org_id: str | UUID, data: ProjectCreate, created_by_id: str | UUID) -> Project:
        o_val = UUID(str(org_id)) if not isinstance(org_id, UUID) else org_id
        c_val = UUID(str(created_by_id)) if created_by_id and not isinstance(created_by_id, UUID) else created_by_id
        project = Project(
            organization_id=o_val,
            name=data.name.strip(),
            key=data.key.upper(),
            description=data.description,
            status=ProjectStatus.ACTIVE,
            created_by=c_val,
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        logger.info(f"Created project: {project.key} - {project.name}")
        return project

    def update(self, project_id: str | UUID, data: ProjectUpdate) -> Optional[Project]:
        project = self.get_by_id(project_id)
        if not project:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)
        self.db.commit()
        self.db.refresh(project)
        return project

    def archive(self, project_id: str | UUID) -> bool:
        project = self.get_by_id(project_id)
        if not project:
            return False
        project.status = ProjectStatus.ARCHIVED
        self.db.commit()
        logger.info(f"Archived project: {project.key} - {project.name}")
        return True
