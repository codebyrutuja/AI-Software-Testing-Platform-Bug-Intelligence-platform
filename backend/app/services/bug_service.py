"""
app/services/bug_service.py
───────────────────────────
PURPOSE:
  Business logic for Phase 7 Bug Tracker & Defect Management:
  1. Tenant-safe bug creation, linking to requirements & test cases
  2. Sequential bug key generation
  3. Quick-create bug from failed test execution items
  4. Bug lifecycle management (Open -> In Progress -> Resolved -> Closed)
"""
import logging
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.bug import BugPriority, BugSeverity, BugStatus
from app.models.project import ProjectStatus
from app.models.user import User
from app.repositories.bug_repository import BugRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.repositories.test_run_repository import TestRunRepository
from app.repositories.user_repository import UserRepository
from app.schemas.bug import (
    BugCreate,
    BugListResponse,
    BugResponse,
    BugStatsResponse,
    BugUpdate,
)

logger = logging.getLogger(__name__)


class BugService:
    def __init__(self, db: Session):
        self.db = db
        self.bug_repo = BugRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.tc_repo = TestCaseRepository(db)
        self.req_repo = RequirementRepository(db)
        self.run_repo = TestRunRepository(db)
        self.user_repo = UserRepository(db)

    def _verify_project_access(self, project_id: UUID, current_user: User):
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

    def _to_bug_response(self, bug) -> BugResponse:
        return BugResponse(
            id=bug.id,
            project_id=bug.project_id,
            bug_key=bug.bug_key,
            title=bug.title,
            description=bug.description,
            steps_to_reproduce=bug.steps_to_reproduce,
            expected_behavior=bug.expected_behavior,
            actual_behavior=bug.actual_behavior,
            severity=bug.severity,
            priority=bug.priority,
            status=bug.status,
            environment=bug.environment,
            browser_os=bug.browser_os,
            test_run_item_id=bug.test_run_item_id,
            test_case_id=bug.test_case_id,
            tc_key=bug.test_case.tc_key if bug.test_case else None,
            tc_title=bug.test_case.title if bug.test_case else None,
            requirement_id=bug.requirement_id,
            requirement_key=bug.requirement.req_key if bug.requirement else None,
            requirement_title=bug.requirement.title if bug.requirement else None,
            reported_by=bug.reported_by,
            reporter_name=bug.reporter.full_name if bug.reporter else None,
            assigned_to=bug.assigned_to,
            assignee_name=bug.assignee.full_name if bug.assignee else None,
            reported_at=bug.reported_at,
            resolved_at=bug.resolved_at,
            created_at=bug.created_at,
            updated_at=bug.updated_at,
        )

    def create_bug(
        self, project_id: UUID, data: BugCreate, current_user: User
    ) -> BugResponse:
        project = self._verify_project_access(project_id, current_user)

        # Validate test case if given
        tc_id = data.test_case_id
        if tc_id:
            tc = self.tc_repo.get_case_by_id(tc_id, project.id)
            if not tc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Test case not found in this project.",
                )

        # Validate requirement if given
        if data.requirement_id:
            req = self.req_repo.get_requirement_by_id(data.requirement_id, project.id)
            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Requirement not found in this project.",
                )

        # Validate test_run_item if given
        if data.test_run_item_id:
            item = self.run_repo.get_item_by_id(data.test_run_item_id)
            if not item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Test run item not found.",
                )
            if item.test_run.project_id != project.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Test run item does not belong to this project.",
                )
            # Auto-link test_case_id from item if not provided
            if not tc_id and item.test_case_id:
                tc_id = item.test_case_id

        # Validate severity & priority
        if data.severity not in BugSeverity.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"severity must be one of: {', '.join(BugSeverity.ALL)}",
            )
        if data.priority not in BugPriority.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"priority must be one of: {', '.join(BugPriority.ALL)}",
            )

        bug_key = self.bug_repo.get_next_bug_key(project.id, project.key)
        created = self.bug_repo.create_bug(
            project_id=project.id,
            bug_key=bug_key,
            title=data.title,
            description=data.description,
            steps_to_reproduce=data.steps_to_reproduce,
            expected_behavior=data.expected_behavior,
            actual_behavior=data.actual_behavior,
            severity=data.severity,
            priority=data.priority,
            environment=data.environment,
            browser_os=data.browser_os,
            test_run_item_id=data.test_run_item_id,
            test_case_id=tc_id,
            requirement_id=data.requirement_id,
            reported_by=current_user.id,
            assigned_to=data.assigned_to,
        )
        return self._to_bug_response(created)

    def quick_report_from_run_item(
        self,
        project_id: UUID,
        run_id: UUID,
        item_id: UUID,
        data: BugCreate,
        current_user: User,
    ) -> BugResponse:
        project = self._verify_project_access(project_id, current_user)
        run = self.run_repo.get_run_by_id(run_id, project.id)
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run not found.",
            )
        item = self.run_repo.get_item_by_id(item_id)
        if not item or item.test_run_id != run_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test run item not found.",
            )

        data.test_run_item_id = item.id
        if not data.test_case_id and item.test_case_id:
            data.test_case_id = item.test_case_id
        if not data.actual_behavior and item.failure_notes:
            data.actual_behavior = item.failure_notes

        return self.create_bug(project_id, data, current_user)

    def list_bugs(
        self,
        project_id: UUID,
        current_user: User,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> BugListResponse:
        project = self._verify_project_access(project_id, current_user)
        bugs = self.bug_repo.list_bugs(
            project_id=project.id,
            status=status,
            severity=severity,
            priority=priority,
            assigned_to=assigned_to,
            search=search,
            skip=skip,
            limit=limit,
        )
        total = self.bug_repo.count_bugs(
            project_id=project.id,
            status=status,
            severity=severity,
            priority=priority,
            assigned_to=assigned_to,
            search=search,
        )
        return BugListResponse(
            items=[self._to_bug_response(b) for b in bugs],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_bug(
        self, project_id: UUID, bug_id: UUID, current_user: User
    ) -> BugResponse:
        self._verify_project_access(project_id, current_user)
        bug = self.bug_repo.get_bug_by_id(bug_id, project_id)
        if not bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found.",
            )
        return self._to_bug_response(bug)

    def update_bug(
        self,
        project_id: UUID,
        bug_id: UUID,
        data: BugUpdate,
        current_user: User,
    ) -> BugResponse:
        self._verify_project_access(project_id, current_user)
        bug = self.bug_repo.get_bug_by_id(bug_id, project_id)
        if not bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found.",
            )

        if data.severity and data.severity not in BugSeverity.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"severity must be one of: {', '.join(BugSeverity.ALL)}",
            )
        if data.priority and data.priority not in BugPriority.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"priority must be one of: {', '.join(BugPriority.ALL)}",
            )
        if data.status and data.status not in BugStatus.ALL:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"status must be one of: {', '.join(BugStatus.ALL)}",
            )

        updated = self.bug_repo.update_bug(
            bug_id=bug_id,
            title=data.title,
            description=data.description,
            steps_to_reproduce=data.steps_to_reproduce,
            expected_behavior=data.expected_behavior,
            actual_behavior=data.actual_behavior,
            severity=data.severity,
            priority=data.priority,
            status=data.status,
            environment=data.environment,
            browser_os=data.browser_os,
            assigned_to=data.assigned_to,
        )
        return self._to_bug_response(updated)

    def delete_bug(
        self, project_id: UUID, bug_id: UUID, current_user: User
    ) -> dict:
        self._verify_project_access(project_id, current_user)
        bug = self.bug_repo.get_bug_by_id(bug_id, project_id)
        if not bug:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bug not found.",
            )
        self.bug_repo.delete_bug(bug_id)
        return {"message": "Bug deleted successfully."}

    def get_stats(
        self, project_id: UUID, current_user: User
    ) -> BugStatsResponse:
        project = self._verify_project_access(project_id, current_user)
        stats = self.bug_repo.get_bug_stats(project.id)
        return BugStatsResponse(
            total=stats["total"],
            open=stats["open"],
            in_progress=stats["in_progress"],
            resolved=stats["resolved"],
            closed=stats["closed"],
            wont_fix=stats["wont_fix"],
            by_severity=stats["by_severity"],
        )
