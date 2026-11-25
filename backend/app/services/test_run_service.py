"""
app/services/test_run_service.py
─────────────────────────────────
PURPOSE:
  Business logic for Phase 6 Test Execution Runs & Results Logging:
  1. Tenant-safe run creation with test case validation
  2. Sequential run key generation
  3. Auto status transitions (planned → in_progress → completed)
  4. Result recording per test case item
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import ProjectStatus
from app.models.test_run import RunResult, RunStatus
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.repositories.test_run_repository import TestRunRepository
from app.schemas.test_run import (
    RunCreate,
    RunItemResponse,
    RunItemUpdate,
    RunListResponse,
    RunResponse,
    RunUpdate,
)

logger = logging.getLogger(__name__)


class TestRunService:
    __test__ = False

    def __init__(self, db: Session):
        self.db = db
        self.run_repo = TestRunRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.tc_repo = TestCaseRepository(db)

    def _verify_project_access(self, project_id: UUID, current_user: User):
        """Enforces tenant isolation — project must exist and user must be member."""
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

    def _to_item_response(self, item) -> RunItemResponse:
        tc = item.test_case
        return RunItemResponse(
            id=item.id,
            test_run_id=item.test_run_id,
            test_case_id=item.test_case_id,
            tc_key=tc.tc_key if tc else None,
            tc_title=tc.title if tc else None,
            result=item.result,
            failure_notes=item.failure_notes,
            actual_duration_minutes=item.actual_duration_minutes,
            executed_by=item.executed_by,
            executed_at=item.executed_at,
            created_at=item.created_at,
        )

    def _to_run_response(self, run) -> RunResponse:
        progress = self.run_repo.get_run_progress(run.id)
        return RunResponse(
            id=run.id,
            project_id=run.project_id,
            run_key=run.run_key,
            name=run.name,
            description=run.description,
            status=run.status,
            environment=run.environment,
            created_by=run.created_by,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
            total_count=progress["total"],
            passed_count=progress["passed"],
            failed_count=progress["failed"],
            blocked_count=progress["blocked"],
            skipped_count=progress["skipped"],
            not_run_count=progress["not_run"],
            items=[self._to_item_response(i) for i in run.items],
        )

    # ── Public API ─────────────────────────────────────────────────────────────

    def create_run(
        self, project_id: UUID, data: RunCreate, current_user: User
    ) -> RunResponse:
        project = self._verify_project_access(project_id, current_user)

        # Validate all test_case_ids belong to this project
        for tc_id in data.test_case_ids:
            tc = self.tc_repo.get_case_by_id(tc_id, project.id)
            if not tc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Test case {tc_id} not found in this project.",
                )

        # Validate environment value
        valid_envs = ("local", "staging", "qa", "production")
        if data.environment not in valid_envs:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"environment must be one of: {', '.join(valid_envs)}",
            )

        run_key = self.run_repo.get_next_run_key(project.id, project.key)
        run = self.run_repo.create_run(
            project_id=project.id,
            run_key=run_key,
            name=data.name,
            description=data.description,
            environment=data.environment,
            test_case_ids=[UUID(str(tc_id)) for tc_id in data.test_case_ids],
            created_by=current_user.id,
        )
        return self._to_run_response(run)

    def list_runs(
        self,
        project_id: UUID,
        current_user: User,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> RunListResponse:
        project = self._verify_project_access(project_id, current_user)
        runs = self.run_repo.list_runs(project.id, status_filter, skip, limit)
        total = self.run_repo.count_runs(project.id, status_filter)
        return RunListResponse(
            items=[self._to_run_response(r) for r in runs],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_run(
        self, project_id: UUID, run_id: UUID, current_user: User
    ) -> RunResponse:
        self._verify_project_access(project_id, current_user)
        run = self.run_repo.get_run_by_id(run_id, project_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found.",
            )
        return self._to_run_response(run)

    def update_run(
        self, project_id: UUID, run_id: UUID, data: RunUpdate, current_user: User
    ) -> RunResponse:
        self._verify_project_access(project_id, current_user)
        run = self.run_repo.get_run_by_id(run_id, project_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found.",
            )
        updated = self.run_repo.update_run(
            run_id=run_id,
            name=data.name,
            description=data.description,
            status=data.status,
            environment=data.environment,
        )
        return self._to_run_response(updated)

    def delete_run(
        self, project_id: UUID, run_id: UUID, current_user: User
    ) -> dict:
        self._verify_project_access(project_id, current_user)
        run = self.run_repo.get_run_by_id(run_id, project_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found.",
            )
        self.run_repo.delete_run(run_id)
        return {"message": "Test run deleted successfully."}

    def submit_item_result(
        self,
        project_id: UUID,
        run_id: UUID,
        item_id: UUID,
        data: RunItemUpdate,
        current_user: User,
    ) -> RunItemResponse:
        self._verify_project_access(project_id, current_user)
        run = self.run_repo.get_run_by_id(run_id, project_id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found.",
            )
        if run.status == RunStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update results on a completed run.",
            )

        # Validate result value
        valid_results = (RunResult.PASSED, RunResult.FAILED, RunResult.BLOCKED, RunResult.SKIPPED)
        if data.result not in valid_results:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"result must be one of: {', '.join(valid_results)}",
            )

        # Validate item belongs to this run
        item = self.run_repo.get_item_by_id(item_id)
        if not item or item.test_run_id != run_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run item not found in this run.",
            )

        # Require failure_notes when result is failed
        if data.result == RunResult.FAILED and not data.failure_notes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="failure_notes is required when result is 'failed'.",
            )

        updated_item = self.run_repo.update_run_item(
            item_id=item_id,
            result=data.result,
            failure_notes=data.failure_notes,
            actual_duration_minutes=data.actual_duration_minutes,
            executed_by=current_user.id,
        )

        # Auto status transition: planned → in_progress on first execution
        if run.status == RunStatus.PLANNED:
            self.run_repo.update_run(run_id=run_id, status=RunStatus.IN_PROGRESS)

        # Auto status transition: in_progress → completed when all items have a result
        progress = self.run_repo.get_run_progress(run_id)
        if progress["not_run"] == 0:
            self.run_repo.update_run(run_id=run_id, status=RunStatus.COMPLETED)

        return self._to_item_response(updated_item)
