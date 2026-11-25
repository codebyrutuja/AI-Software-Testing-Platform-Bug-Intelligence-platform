"""
app/repositories/bug_repository.py
──────────────────────────────────
PURPOSE: All database queries for Bug Tracker & Defect Management (Phase 7).
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.bug import Bug, BugSeverity, BugStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class BugRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_next_bug_key(self, project_id: UUID, project_key: str) -> str:
        """
        Returns next sequential bug key: {PROJECT_KEY}-BUG-{N:02d}
        Example: ECOM-BUG-01, ECOM-BUG-02 …
        """
        prefix = f"{project_key.upper()}-BUG-"
        keys = (
            self.db.query(Bug.bug_key)
            .filter(Bug.project_id == project_id)
            .filter(Bug.bug_key.like(f"{prefix}%"))
            .all()
        )
        max_num = 0
        for (k,) in keys:
            suffix = k[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        return f"{prefix}{max_num + 1:02d}"

    def create_bug(
        self,
        project_id: UUID,
        bug_key: str,
        title: str,
        description: Optional[str] = None,
        steps_to_reproduce: Optional[str] = None,
        expected_behavior: Optional[str] = None,
        actual_behavior: Optional[str] = None,
        severity: str = "medium",
        priority: str = "medium",
        environment: Optional[str] = None,
        browser_os: Optional[str] = None,
        test_run_item_id: Optional[UUID] = None,
        test_case_id: Optional[UUID] = None,
        requirement_id: Optional[UUID] = None,
        reported_by: Optional[UUID] = None,
        assigned_to: Optional[UUID] = None,
    ) -> Bug:
        bug = Bug(
            project_id=project_id,
            bug_key=bug_key,
            title=title.strip(),
            description=description.strip() if description else None,
            steps_to_reproduce=steps_to_reproduce.strip() if steps_to_reproduce else None,
            expected_behavior=expected_behavior.strip() if expected_behavior else None,
            actual_behavior=actual_behavior.strip() if actual_behavior else None,
            severity=severity,
            priority=priority,
            status=BugStatus.OPEN,
            environment=environment.strip() if environment else None,
            browser_os=browser_os.strip() if browser_os else None,
            test_run_item_id=test_run_item_id,
            test_case_id=test_case_id,
            requirement_id=requirement_id,
            reported_by=reported_by,
            assigned_to=assigned_to,
        )
        self.db.add(bug)
        self.db.commit()
        return self.get_bug_by_id(bug.id, project_id)

    def get_bug_by_id(
        self, bug_id: UUID, project_id: Optional[UUID] = None
    ) -> Optional[Bug]:
        query = (
            self.db.query(Bug)
            .options(
                joinedload(Bug.test_case),
                joinedload(Bug.requirement),
                joinedload(Bug.reporter),
                joinedload(Bug.assignee),
            )
            .filter(Bug.id == bug_id)
        )
        if project_id:
            query = query.filter(Bug.project_id == project_id)
        return query.first()

    def list_bugs(
        self,
        project_id: UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Bug]:
        query = (
            self.db.query(Bug)
            .options(
                joinedload(Bug.test_case),
                joinedload(Bug.requirement),
                joinedload(Bug.reporter),
                joinedload(Bug.assignee),
            )
            .filter(Bug.project_id == project_id)
        )
        if status:
            query = query.filter(Bug.status == status)
        if severity:
            query = query.filter(Bug.severity == severity)
        if priority:
            query = query.filter(Bug.priority == priority)
        if assigned_to:
            query = query.filter(Bug.assigned_to == assigned_to)
        if search:
            pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Bug.title.ilike(pat),
                    Bug.description.ilike(pat),
                    Bug.bug_key.ilike(pat),
                )
            )
        return (
            query.order_by(desc(Bug.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_bugs(
        self,
        project_id: UUID,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        search: Optional[str] = None,
    ) -> int:
        query = self.db.query(func.count(Bug.id)).filter(Bug.project_id == project_id)
        if status:
            query = query.filter(Bug.status == status)
        if severity:
            query = query.filter(Bug.severity == severity)
        if priority:
            query = query.filter(Bug.priority == priority)
        if assigned_to:
            query = query.filter(Bug.assigned_to == assigned_to)
        if search:
            pat = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Bug.title.ilike(pat),
                    Bug.description.ilike(pat),
                    Bug.bug_key.ilike(pat),
                )
            )
        return query.scalar() or 0

    def update_bug(
        self,
        bug_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        steps_to_reproduce: Optional[str] = None,
        expected_behavior: Optional[str] = None,
        actual_behavior: Optional[str] = None,
        severity: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        browser_os: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
    ) -> Optional[Bug]:
        bug = self.get_bug_by_id(bug_id)
        if not bug:
            return None

        if title is not None:
            bug.title = title.strip()
        if description is not None:
            bug.description = description.strip() if description else None
        if steps_to_reproduce is not None:
            bug.steps_to_reproduce = steps_to_reproduce.strip() if steps_to_reproduce else None
        if expected_behavior is not None:
            bug.expected_behavior = expected_behavior.strip() if expected_behavior else None
        if actual_behavior is not None:
            bug.actual_behavior = actual_behavior.strip() if actual_behavior else None
        if severity is not None:
            bug.severity = severity
        if priority is not None:
            bug.priority = priority
        if environment is not None:
            bug.environment = environment.strip() if environment else None
        if browser_os is not None:
            bug.browser_os = browser_os.strip() if browser_os else None
        if assigned_to is not None:
            bug.assigned_to = assigned_to

        if status is not None:
            bug.status = status
            if status == BugStatus.RESOLVED and bug.resolved_at is None:
                bug.resolved_at = datetime.now(timezone.utc)
            elif status != BugStatus.RESOLVED:
                bug.resolved_at = None

        self.db.commit()
        return self.get_bug_by_id(bug_id)

    def delete_bug(self, bug_id: UUID) -> bool:
        bug = self.get_bug_by_id(bug_id)
        if not bug:
            return False
        self.db.delete(bug)
        self.db.commit()
        return True

    def get_bug_stats(self, project_id: UUID) -> Dict:
        bugs = self.db.query(Bug.status, Bug.severity).filter(Bug.project_id == project_id).all()
        stats = {
            "total": len(bugs),
            "open": 0,
            "in_progress": 0,
            "resolved": 0,
            "closed": 0,
            "wont_fix": 0,
            "by_severity": {s: 0 for s in BugSeverity.ALL},
        }
        for st, sev in bugs:
            if st in stats:
                stats[st] += 1
            if sev in stats["by_severity"]:
                stats["by_severity"][sev] += 1
        return stats
