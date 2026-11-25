"""
app/repositories/test_case_repository.py
────────────────────────────────────────
PURPOSE: All database queries for TestSuites, TestCases, and TestSteps (Phase 5).
"""
import logging
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.test_case import (
    TestCase,
    TestPriority,
    TestStatus,
    TestStep,
    TestSuite,
    TestType,
)

logger = logging.getLogger(__name__)


class TestCaseRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Test Suite Operations ───────────────────────────────────────────────────

    def list_suites(self, project_id: str | UUID) -> List[tuple[TestSuite, int]]:
        """
        Lists all suites for a project along with the count of direct test cases.
        """
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id

        # Subquery for case count
        count_subquery = (
            self.db.query(
                TestCase.suite_id,
                func.count(TestCase.id).label("case_count"),
            )
            .filter(TestCase.project_id == p_val)
            .group_by(TestCase.suite_id)
            .subquery()
        )

        results = (
            self.db.query(TestSuite, func.coalesce(count_subquery.c.case_count, 0))
            .outerjoin(count_subquery, TestSuite.id == count_subquery.c.suite_id)
            .filter(TestSuite.project_id == p_val)
            .order_by(TestSuite.name)
            .all()
        )

        return results

    def get_suite_by_id(
        self, suite_id: str | UUID, project_id: Optional[str | UUID] = None
    ) -> Optional[TestSuite]:
        s_val = UUID(str(suite_id)) if not isinstance(suite_id, UUID) else suite_id
        query = self.db.query(TestSuite).filter(TestSuite.id == s_val)
        if project_id:
            p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
            query = query.filter(TestSuite.project_id == p_val)
        return query.first()

    def create_suite(
        self,
        project_id: str | UUID,
        name: str,
        description: Optional[str] = None,
        parent_suite_id: Optional[str | UUID] = None,
    ) -> TestSuite:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        parent_val = (
            UUID(str(parent_suite_id))
            if parent_suite_id and not isinstance(parent_suite_id, UUID)
            else parent_suite_id
        )

        suite = TestSuite(
            project_id=p_val,
            parent_suite_id=parent_val,
            name=name.strip(),
            description=description.strip() if description else None,
        )
        self.db.add(suite)
        self.db.commit()
        self.db.refresh(suite)
        return suite

    def update_suite(
        self,
        suite_id: str | UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_suite_id: Optional[str | UUID] = None,
    ) -> Optional[TestSuite]:
        suite = self.get_suite_by_id(suite_id)
        if not suite:
            return None

        if name is not None:
            suite.name = name.strip()
        if description is not None:
            suite.description = description.strip() if description else None
        if parent_suite_id is not None:
            suite.parent_suite_id = (
                UUID(str(parent_suite_id))
                if not isinstance(parent_suite_id, UUID)
                else parent_suite_id
            )

        self.db.commit()
        self.db.refresh(suite)
        return suite

    def delete_suite(self, suite_id: str | UUID) -> bool:
        suite = self.get_suite_by_id(suite_id)
        if not suite:
            return False
        self.db.delete(suite)
        self.db.commit()
        return True

    # ── Key Generation Helper ───────────────────────────────────────────────────

    def get_next_tc_key(self, project_id: str | UUID, project_key: str) -> str:
        """
        Calculates the next sequential test case key for a project.
        Format: {PROJECT_KEY}-TC-{NUMBER}, e.g. ECOM-TC-01
        """
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        prefix = f"{project_key.upper()}-TC-"

        keys = (
            self.db.query(TestCase.tc_key)
            .filter(TestCase.project_id == p_val)
            .filter(TestCase.tc_key.like(f"{prefix}%"))
            .all()
        )

        max_num = 0
        for (k,) in keys:
            suffix = k[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))

        next_num = max_num + 1
        return f"{prefix}{next_num:02d}"

    # ── Test Case Operations ────────────────────────────────────────────────────

    def get_case_by_id(
        self, case_id: str | UUID, project_id: Optional[str | UUID] = None
    ) -> Optional[TestCase]:
        c_val = UUID(str(case_id)) if not isinstance(case_id, UUID) else case_id
        query = (
            self.db.query(TestCase)
            .options(
                joinedload(TestCase.steps),
                joinedload(TestCase.suite),
                joinedload(TestCase.requirement),
            )
            .filter(TestCase.id == c_val)
        )
        if project_id:
            p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
            query = query.filter(TestCase.project_id == p_val)
        return query.first()

    def list_cases(
        self,
        project_id: str | UUID,
        suite_id: Optional[str | UUID] = None,
        requirement_id: Optional[str | UUID] = None,
        test_type: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[TestCase]:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        query = (
            self.db.query(TestCase)
            .options(
                joinedload(TestCase.steps),
                joinedload(TestCase.suite),
                joinedload(TestCase.requirement),
            )
            .filter(TestCase.project_id == p_val)
        )

        if suite_id:
            s_val = UUID(str(suite_id)) if not isinstance(suite_id, UUID) else suite_id
            query = query.filter(TestCase.suite_id == s_val)
        if requirement_id:
            r_val = UUID(str(requirement_id)) if not isinstance(requirement_id, UUID) else requirement_id
            query = query.filter(TestCase.requirement_id == r_val)
        if test_type:
            query = query.filter(TestCase.test_type == test_type)
        if priority:
            query = query.filter(TestCase.priority == priority)
        if status:
            query = query.filter(TestCase.status == status)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    TestCase.title.ilike(search_pattern),
                    TestCase.description.ilike(search_pattern),
                    TestCase.tc_key.ilike(search_pattern),
                )
            )

        return (
            query.order_by(desc(TestCase.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_cases(
        self,
        project_id: str | UUID,
        suite_id: Optional[str | UUID] = None,
        requirement_id: Optional[str | UUID] = None,
        test_type: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
    ) -> int:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        query = self.db.query(func.count(TestCase.id)).filter(TestCase.project_id == p_val)

        if suite_id:
            s_val = UUID(str(suite_id)) if not isinstance(suite_id, UUID) else suite_id
            query = query.filter(TestCase.suite_id == s_val)
        if requirement_id:
            r_val = UUID(str(requirement_id)) if not isinstance(requirement_id, UUID) else requirement_id
            query = query.filter(TestCase.requirement_id == r_val)
        if test_type:
            query = query.filter(TestCase.test_type == test_type)
        if priority:
            query = query.filter(TestCase.priority == priority)
        if status:
            query = query.filter(TestCase.status == status)
        if search:
            search_pattern = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    TestCase.title.ilike(search_pattern),
                    TestCase.description.ilike(search_pattern),
                    TestCase.tc_key.ilike(search_pattern),
                )
            )

        return query.scalar() or 0

    def create_case(
        self,
        project_id: str | UUID,
        tc_key: str,
        title: str,
        suite_id: Optional[str | UUID] = None,
        requirement_id: Optional[str | UUID] = None,
        description: Optional[str] = None,
        preconditions: Optional[str] = None,
        test_type: str = TestType.MANUAL,
        priority: str = TestPriority.MEDIUM,
        status: str = TestStatus.ACTIVE,
        estimated_duration_minutes: int = 5,
        created_by: Optional[str | UUID] = None,
        steps_data: Optional[List[dict]] = None,
    ) -> TestCase:
        p_val = UUID(str(project_id)) if not isinstance(project_id, UUID) else project_id
        s_val = UUID(str(suite_id)) if suite_id and not isinstance(suite_id, UUID) else suite_id
        r_val = UUID(str(requirement_id)) if requirement_id and not isinstance(requirement_id, UUID) else requirement_id
        c_val = UUID(str(created_by)) if created_by and not isinstance(created_by, UUID) else created_by

        tc = TestCase(
            project_id=p_val,
            suite_id=s_val,
            requirement_id=r_val,
            tc_key=tc_key,
            title=title.strip(),
            description=description.strip() if description else None,
            preconditions=preconditions.strip() if preconditions else None,
            test_type=test_type,
            priority=priority,
            status=status,
            estimated_duration_minutes=estimated_duration_minutes,
            created_by=c_val,
        )
        self.db.add(tc)
        self.db.flush()

        if steps_data:
            for idx, step_dict in enumerate(steps_data):
                step = TestStep(
                    test_case_id=tc.id,
                    step_number=step_dict.get("step_number", idx + 1),
                    action=step_dict["action"].strip(),
                    test_data=step_dict.get("test_data", "").strip() or None if step_dict.get("test_data") else None,
                    expected_result=step_dict["expected_result"].strip(),
                )
                self.db.add(step)

        self.db.commit()
        return self.get_case_by_id(tc.id, p_val)

    def update_case(
        self,
        case_id: str | UUID,
        title: Optional[str] = None,
        suite_id: Optional[str | UUID] = None,
        requirement_id: Optional[str | UUID] = None,
        description: Optional[str] = None,
        preconditions: Optional[str] = None,
        test_type: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        estimated_duration_minutes: Optional[int] = None,
        steps_data: Optional[List[dict]] = None,
    ) -> Optional[TestCase]:
        tc = self.get_case_by_id(case_id)
        if not tc:
            return None

        if title is not None:
            tc.title = title.strip()
        if suite_id is not None:
            tc.suite_id = UUID(str(suite_id)) if suite_id and not isinstance(suite_id, UUID) else suite_id
        if requirement_id is not None:
            tc.requirement_id = UUID(str(requirement_id)) if requirement_id and not isinstance(requirement_id, UUID) else requirement_id
        if description is not None:
            tc.description = description.strip() if description else None
        if preconditions is not None:
            tc.preconditions = preconditions.strip() if preconditions else None
        if test_type is not None:
            tc.test_type = test_type
        if priority is not None:
            tc.priority = priority
        if status is not None:
            tc.status = status
        if estimated_duration_minutes is not None:
            tc.estimated_duration_minutes = estimated_duration_minutes

        if steps_data is not None:
            # Replace steps atomically
            self.db.query(TestStep).filter(TestStep.test_case_id == tc.id).delete()
            for idx, step_dict in enumerate(steps_data):
                step = TestStep(
                    test_case_id=tc.id,
                    step_number=step_dict.get("step_number", idx + 1),
                    action=step_dict["action"].strip(),
                    test_data=step_dict.get("test_data", "").strip() or None if step_dict.get("test_data") else None,
                    expected_result=step_dict["expected_result"].strip(),
                )
                self.db.add(step)

        self.db.commit()
        return self.get_case_by_id(tc.id)

    def delete_case(self, case_id: str | UUID) -> bool:
        tc = self.get_case_by_id(case_id)
        if not tc:
            return False
        self.db.delete(tc)
        self.db.commit()
        return True
