"""
app/services/test_case_service.py
─────────────────────────────────
PURPOSE:
  Business logic for Phase 5 Test Cases & Test Suites Management:
  1. Test Suite hierarchy and folder structure
  2. Test Case authoring with sequential keys (e.g. AUTH-TC-01)
  3. Step-by-step procedures and requirement linking
  4. Multi-Tenant Project Scoping & Authorization
"""
import logging
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.project import Project, ProjectStatus
from app.models.user import User
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.requirement_repository import RequirementRepository
from app.repositories.test_case_repository import TestCaseRepository
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseListResponse,
    TestCaseResponse,
    TestCaseUpdate,
    TestStepResponse,
    TestSuiteCreate,
    TestSuiteResponse,
    TestSuiteUpdate,
)

logger = logging.getLogger(__name__)


class TestCaseService:
    __test__ = False

    def __init__(self, db: Session):
        self.db = db
        self.tc_repo = TestCaseRepository(db)
        self.project_repo = ProjectRepository(db)
        self.org_repo = OrganizationRepository(db)
        self.req_repo = RequirementRepository(db)

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

    # ── Test Suite Operations ───────────────────────────────────────────────────

    def list_suites(
        self, project_id: str | UUID, current_user: User
    ) -> List[TestSuiteResponse]:
        project = self._verify_project_access(project_id, current_user)
        results = self.tc_repo.list_suites(project.id)
        return [
            TestSuiteResponse(
                id=suite.id,
                project_id=suite.project_id,
                parent_suite_id=suite.parent_suite_id,
                name=suite.name,
                description=suite.description,
                created_at=suite.created_at,
                case_count=count,
            )
            for suite, count in results
        ]

    def create_suite(
        self, project_id: str | UUID, data: TestSuiteCreate, current_user: User
    ) -> TestSuiteResponse:
        project = self._verify_project_access(project_id, current_user)

        if data.parent_suite_id:
            parent = self.tc_repo.get_suite_by_id(data.parent_suite_id, project.id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent test suite not found in this project.",
                )

        suite = self.tc_repo.create_suite(
            project_id=project.id,
            name=data.name,
            description=data.description,
            parent_suite_id=data.parent_suite_id,
        )
        return TestSuiteResponse(
            id=suite.id,
            project_id=suite.project_id,
            parent_suite_id=suite.parent_suite_id,
            name=suite.name,
            description=suite.description,
            created_at=suite.created_at,
            case_count=0,
        )

    def update_suite(
        self,
        project_id: str | UUID,
        suite_id: str | UUID,
        data: TestSuiteUpdate,
        current_user: User,
    ) -> TestSuiteResponse:
        self._verify_project_access(project_id, current_user)
        suite = self.tc_repo.get_suite_by_id(suite_id, project_id)
        if not suite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test suite not found.",
            )

        updated = self.tc_repo.update_suite(
            suite_id=suite_id,
            name=data.name,
            description=data.description,
            parent_suite_id=data.parent_suite_id,
        )
        return TestSuiteResponse.model_validate(updated)

    def delete_suite(
        self, project_id: str | UUID, suite_id: str | UUID, current_user: User
    ) -> dict:
        self._verify_project_access(project_id, current_user)
        suite = self.tc_repo.get_suite_by_id(suite_id, project_id)
        if not suite:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test suite not found.",
            )

        self.tc_repo.delete_suite(suite_id)
        return {"message": "Test suite deleted successfully."}

    # ── Test Case Operations ────────────────────────────────────────────────────

    def _to_case_response(self, tc) -> TestCaseResponse:
        return TestCaseResponse(
            id=tc.id,
            project_id=tc.project_id,
            suite_id=tc.suite_id,
            suite_name=tc.suite.name if tc.suite else None,
            requirement_id=tc.requirement_id,
            requirement_key=tc.requirement.req_key if tc.requirement else None,
            requirement_title=tc.requirement.title if tc.requirement else None,
            tc_key=tc.tc_key,
            title=tc.title,
            description=tc.description,
            preconditions=tc.preconditions,
            test_type=tc.test_type,
            priority=tc.priority,
            status=tc.status,
            estimated_duration_minutes=tc.estimated_duration_minutes,
            created_by=tc.created_by,
            created_at=tc.created_at,
            updated_at=tc.updated_at,
            steps=[TestStepResponse.model_validate(s) for s in tc.steps],
        )

    def list_cases(
        self,
        project_id: str | UUID,
        current_user: User,
        suite_id: Optional[str | UUID] = None,
        requirement_id: Optional[str | UUID] = None,
        test_type: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> TestCaseListResponse:
        project = self._verify_project_access(project_id, current_user)

        items = self.tc_repo.list_cases(
            project_id=project.id,
            suite_id=suite_id,
            requirement_id=requirement_id,
            test_type=test_type,
            priority=priority,
            status=status,
            search=search,
            skip=skip,
            limit=limit,
        )
        total = self.tc_repo.count_cases(
            project_id=project.id,
            suite_id=suite_id,
            requirement_id=requirement_id,
            test_type=test_type,
            priority=priority,
            status=status,
            search=search,
        )

        return TestCaseListResponse(
            items=[self._to_case_response(tc) for tc in items],
            total=total,
            skip=skip,
            limit=limit,
        )

    def get_case(
        self, project_id: str | UUID, case_id: str | UUID, current_user: User
    ) -> TestCaseResponse:
        self._verify_project_access(project_id, current_user)
        tc = self.tc_repo.get_case_by_id(case_id, project_id)
        if not tc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found in this project.",
            )
        return self._to_case_response(tc)

    def create_case(
        self, project_id: str | UUID, data: TestCaseCreate, current_user: User
    ) -> TestCaseResponse:
        project = self._verify_project_access(project_id, current_user)

        # Validate suite if specified
        if data.suite_id:
            suite = self.tc_repo.get_suite_by_id(data.suite_id, project.id)
            if not suite:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified test suite not found in this project.",
                )

        # Validate requirement if specified
        if data.requirement_id:
            req = self.req_repo.get_requirement_by_id(data.requirement_id, project.id)
            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified requirement not found in this project.",
                )

        tc_key = self.tc_repo.get_next_tc_key(project.id, project.key)

        steps_dicts = [s.model_dump() for s in data.steps] if data.steps else []

        created = self.tc_repo.create_case(
            project_id=project.id,
            tc_key=tc_key,
            title=data.title,
            suite_id=data.suite_id,
            requirement_id=data.requirement_id,
            description=data.description,
            preconditions=data.preconditions,
            test_type=data.test_type,
            priority=data.priority,
            status=data.status,
            estimated_duration_minutes=data.estimated_duration_minutes,
            created_by=current_user.id,
            steps_data=steps_dicts,
        )
        return self._to_case_response(created)

    def update_case(
        self,
        project_id: str | UUID,
        case_id: str | UUID,
        data: TestCaseUpdate,
        current_user: User,
    ) -> TestCaseResponse:
        project = self._verify_project_access(project_id, current_user)
        existing = self.tc_repo.get_case_by_id(case_id, project.id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found in this project.",
            )

        if data.suite_id:
            suite = self.tc_repo.get_suite_by_id(data.suite_id, project.id)
            if not suite:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified test suite not found in this project.",
                )

        if data.requirement_id:
            req = self.req_repo.get_requirement_by_id(data.requirement_id, project.id)
            if not req:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified requirement not found in this project.",
                )

        steps_dicts = [s.model_dump() for s in data.steps] if data.steps is not None else None

        updated = self.tc_repo.update_case(
            case_id=case_id,
            title=data.title,
            suite_id=data.suite_id,
            requirement_id=data.requirement_id,
            description=data.description,
            preconditions=data.preconditions,
            test_type=data.test_type,
            priority=data.priority,
            status=data.status,
            estimated_duration_minutes=data.estimated_duration_minutes,
            steps_data=steps_dicts,
        )
        return self._to_case_response(updated)

    def delete_case(
        self, project_id: str | UUID, case_id: str | UUID, current_user: User
    ) -> dict:
        self._verify_project_access(project_id, current_user)
        existing = self.tc_repo.get_case_by_id(case_id, project_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test case not found in this project.",
            )

        self.tc_repo.delete_case(case_id)
        return {"message": "Test case deleted successfully."}

