"""
app/repositories/test_run_repository.py
────────────────────────────────────────
PURPOSE: All database queries for TestRun and TestRunItem (Phase 6).
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session, joinedload

from app.models.test_run import RunResult, RunStatus, TestRun, TestRunItem

logger = logging.getLogger(__name__)


class TestRunRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Key Generation ─────────────────────────────────────────────────────────

    def get_next_run_key(self, project_id: UUID, project_key: str) -> str:
        """
        Returns next sequential run key: {PROJECT_KEY}-RUN-{N:02d}
        Example: ECOM-RUN-01, ECOM-RUN-02 …
        """
        prefix = f"{project_key.upper()}-RUN-"
        keys = (
            self.db.query(TestRun.run_key)
            .filter(TestRun.project_id == project_id)
            .filter(TestRun.run_key.like(f"{prefix}%"))
            .all()
        )
        max_num = 0
        for (k,) in keys:
            suffix = k[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        return f"{prefix}{max_num + 1:02d}"

    # ── CRUD Operations ────────────────────────────────────────────────────────

    def create_run(
        self,
        project_id: UUID,
        run_key: str,
        name: str,
        test_case_ids: List[UUID],
        description: Optional[str] = None,
        environment: str = "staging",
        created_by: Optional[UUID] = None,
    ) -> TestRun:
        """
        Creates a TestRun and one TestRunItem per test_case_id (all start as not_run).
        """
        run = TestRun(
            project_id=project_id,
            run_key=run_key,
            name=name.strip(),
            description=description.strip() if description else None,
            environment=environment,
            status=RunStatus.PLANNED,
            created_by=created_by,
        )
        self.db.add(run)
        self.db.flush()  # get run.id before inserting items

        for tc_id in test_case_ids:
            item = TestRunItem(
                test_run_id=run.id,
                test_case_id=tc_id,
                result=RunResult.NOT_RUN,
            )
            self.db.add(item)

        self.db.commit()
        return self.get_run_by_id(run.id, project_id)

    def get_run_by_id(
        self, run_id: UUID, project_id: Optional[UUID] = None
    ) -> Optional[TestRun]:
        query = (
            self.db.query(TestRun)
            .options(
                joinedload(TestRun.items).joinedload(TestRunItem.test_case)
            )
            .filter(TestRun.id == run_id)
        )
        if project_id:
            query = query.filter(TestRun.project_id == project_id)
        return query.first()

    def list_runs(
        self,
        project_id: UUID,
        status_filter: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[TestRun]:
        query = (
            self.db.query(TestRun)
            .options(
                joinedload(TestRun.items).joinedload(TestRunItem.test_case)
            )
            .filter(TestRun.project_id == project_id)
        )
        if status_filter:
            query = query.filter(TestRun.status == status_filter)
        return (
            query.order_by(desc(TestRun.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_runs(self, project_id: UUID, status_filter: Optional[str] = None) -> int:
        query = self.db.query(func.count(TestRun.id)).filter(
            TestRun.project_id == project_id
        )
        if status_filter:
            query = query.filter(TestRun.status == status_filter)
        return query.scalar() or 0

    def update_run(
        self,
        run_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> Optional[TestRun]:
        run = self.get_run_by_id(run_id)
        if not run:
            return None

        if name is not None:
            run.name = name.strip()
        if description is not None:
            run.description = description.strip() if description else None
        if environment is not None:
            run.environment = environment
        if status is not None:
            run.status = status
            # Auto-set timestamps on status transitions
            if status == RunStatus.IN_PROGRESS and run.started_at is None:
                run.started_at = datetime.now(timezone.utc)
            elif status in (RunStatus.COMPLETED, RunStatus.ABORTED) and run.completed_at is None:
                run.completed_at = datetime.now(timezone.utc)

        self.db.commit()
        return self.get_run_by_id(run_id)

    def delete_run(self, run_id: UUID) -> bool:
        run = self.get_run_by_id(run_id)
        if not run:
            return False
        self.db.delete(run)
        self.db.commit()
        return True

    # ── Run Item Operations ────────────────────────────────────────────────────

    def get_item_by_id(self, item_id: UUID) -> Optional[TestRunItem]:
        return (
            self.db.query(TestRunItem)
            .options(joinedload(TestRunItem.test_case))
            .filter(TestRunItem.id == item_id)
            .first()
        )

    def update_run_item(
        self,
        item_id: UUID,
        result: str,
        failure_notes: Optional[str] = None,
        actual_duration_minutes: Optional[int] = None,
        executed_by: Optional[UUID] = None,
    ) -> Optional[TestRunItem]:
        item = self.get_item_by_id(item_id)
        if not item:
            return None

        item.result = result
        item.failure_notes = failure_notes
        item.actual_duration_minutes = actual_duration_minutes
        item.executed_by = executed_by
        item.executed_at = datetime.now(timezone.utc)

        self.db.commit()
        return self.get_item_by_id(item_id)

    def get_run_progress(self, run_id: UUID) -> dict:
        """Returns count of each result type for a run."""
        items = (
            self.db.query(TestRunItem)
            .filter(TestRunItem.test_run_id == run_id)
            .all()
        )
        counts = {r: 0 for r in RunResult.ALL}
        for item in items:
            counts[item.result] = counts.get(item.result, 0) + 1
        return {
            "total": len(items),
            "passed": counts.get(RunResult.PASSED, 0),
            "failed": counts.get(RunResult.FAILED, 0),
            "blocked": counts.get(RunResult.BLOCKED, 0),
            "skipped": counts.get(RunResult.SKIPPED, 0),
            "not_run": counts.get(RunResult.NOT_RUN, 0),
        }
