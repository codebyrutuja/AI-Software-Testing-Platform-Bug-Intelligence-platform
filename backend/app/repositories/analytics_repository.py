"""
app/repositories/analytics_repository.py
─────────────────────────────────────────
PURPOSE:
  Phase 8 — Pure SQL aggregation queries for the Analytics Dashboard.
  READ ONLY — no writes, no schema changes, no new tables.
  Reads from existing Phase 3–7 tables:
    projects, requirements, test_cases, test_runs, test_run_items, bugs
"""
import logging
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.models.bug import Bug, BugSeverity, BugStatus
from app.models.requirement import Requirement
from app.models.test_case import TestCase
from app.models.test_run import TestRun, TestRunItem, RunResult, RunStatus

logger = logging.getLogger(__name__)


class AnalyticsRepository:

    def __init__(self, db: Session):
        self.db = db

    # ── 1. Project Summary Counts ────────────────────────────────────────────
    def get_project_summary(self, project_id: UUID) -> Dict:
        """
        Returns total counts of requirements, test cases, test runs, and bugs
        for a given project. Used for the top-row summary cards.
        """
        total_requirements = (
            self.db.query(func.count(Requirement.id))
            .filter(Requirement.project_id == project_id)
            .scalar() or 0
        )
        total_test_cases = (
            self.db.query(func.count(TestCase.id))
            .filter(TestCase.project_id == project_id)
            .scalar() or 0
        )
        total_test_runs = (
            self.db.query(func.count(TestRun.id))
            .filter(TestRun.project_id == project_id)
            .scalar() or 0
        )
        total_bugs = (
            self.db.query(func.count(Bug.id))
            .filter(Bug.project_id == project_id)
            .scalar() or 0
        )
        return {
            "total_requirements": total_requirements,
            "total_test_cases": total_test_cases,
            "total_test_runs": total_test_runs,
            "total_bugs": total_bugs,
        }

    # ── 2. Test Run Pass/Fail History (last 10 runs) ─────────────────────────
    def get_test_run_pass_fail_stats(self, project_id: UUID) -> List[Dict]:
        """
        Returns the last 10 test runs for a project with their pass/fail/blocked/skipped
        counts and computed pass_rate. Used for the grouped bar chart.
        """
        runs = (
            self.db.query(TestRun)
            .filter(TestRun.project_id == project_id)
            .order_by(TestRun.created_at.desc())
            .limit(10)
            .all()
        )
        # Reverse so oldest is on the left in a chart
        runs = list(reversed(runs))

        result = []
        for run in runs:
            items = run.items
            total = len(items)
            passed = sum(1 for i in items if i.result == RunResult.PASSED)
            failed = sum(1 for i in items if i.result == RunResult.FAILED)
            blocked = sum(1 for i in items if i.result == RunResult.BLOCKED)
            skipped = sum(1 for i in items if i.result == RunResult.SKIPPED)
            not_run = sum(1 for i in items if i.result == RunResult.NOT_RUN)
            pass_rate = round((passed / total * 100), 1) if total > 0 else 0.0

            result.append({
                "run_key": run.run_key,
                "run_name": run.name,
                "status": run.status,
                "environment": run.environment,
                "passed_count": passed,
                "failed_count": failed,
                "blocked_count": blocked,
                "skipped_count": skipped,
                "not_run_count": not_run,
                "total_count": total,
                "pass_rate": pass_rate,
            })
        return result

    # ── 3. Bug Severity Breakdown ─────────────────────────────────────────────
    def get_bug_severity_breakdown(self, project_id: UUID) -> Dict:
        """
        Returns bug counts grouped by severity.
        Used for the doughnut chart.
        """
        rows = (
            self.db.query(Bug.severity, func.count(Bug.id))
            .filter(Bug.project_id == project_id)
            .group_by(Bug.severity)
            .all()
        )
        breakdown = {s: 0 for s in BugSeverity.ALL}
        for severity, count in rows:
            if severity in breakdown:
                breakdown[severity] = count
        return breakdown

    # ── 4. Bug Status Breakdown ───────────────────────────────────────────────
    def get_bug_status_breakdown(self, project_id: UUID) -> Dict:
        """
        Returns bug counts grouped by status.
        Used for the horizontal stacked bar chart.
        """
        rows = (
            self.db.query(Bug.status, func.count(Bug.id))
            .filter(Bug.project_id == project_id)
            .group_by(Bug.status)
            .all()
        )
        breakdown = {s: 0 for s in BugStatus.ALL}
        for bug_status, count in rows:
            if bug_status in breakdown:
                breakdown[bug_status] = count
        return breakdown

    # ── 5. Requirement Coverage ───────────────────────────────────────────────
    def get_requirement_coverage(self, project_id: UUID) -> Dict:
        """
        Computes requirement traceability coverage:
          - covered = requirements that have at least 1 linked test case
          - uncovered = requirements with 0 linked test cases
        Returns coverage_percentage and a list of uncovered requirement summaries.
        """
        all_requirements = (
            self.db.query(Requirement)
            .filter(Requirement.project_id == project_id)
            .all()
        )
        total = len(all_requirements)
        if total == 0:
            return {
                "covered": 0,
                "uncovered": 0,
                "coverage_percentage": 0.0,
                "uncovered_requirements": [],
            }

        # For each requirement, check if any test case links to it
        covered_ids = set(
            row[0]
            for row in (
                self.db.query(TestCase.requirement_id)
                .filter(
                    TestCase.project_id == project_id,
                    TestCase.requirement_id.isnot(None),
                )
                .distinct()
                .all()
            )
        )

        covered = sum(1 for r in all_requirements if r.id in covered_ids)
        uncovered = total - covered
        coverage_pct = round((covered / total * 100), 1)

        uncovered_reqs = [
            {
                "req_key": r.req_key,
                "title": r.title,
                "priority": r.priority,
                "status": r.status,
            }
            for r in all_requirements
            if r.id not in covered_ids
        ]

        return {
            "covered": covered,
            "uncovered": uncovered,
            "coverage_percentage": coverage_pct,
            "uncovered_requirements": uncovered_reqs,
        }

    # ── 6. Overall Health Score ───────────────────────────────────────────────
    def get_health_score(self, project_id: UUID) -> float:
        """
        Computes a weighted QA health score from 0–100:
          pass_rate        * 0.5  (most important — test runs passing)
          coverage_pct     * 0.3  (requirements covered by tests)
          resolution_rate  * 0.2  (bugs resolved vs total)
        Returns a float score rounded to 1 decimal place.
        """
        # pass_rate: average pass rate across last 10 runs
        run_stats = self.get_test_run_pass_fail_stats(project_id)
        if run_stats:
            pass_rate = sum(r["pass_rate"] for r in run_stats) / len(run_stats)
        else:
            pass_rate = 0.0

        # coverage_pct
        coverage = self.get_requirement_coverage(project_id)
        coverage_pct = coverage["coverage_percentage"]

        # bug_resolution_rate: (resolved + closed) / total bugs
        bug_status = self.get_bug_status_breakdown(project_id)
        total_bugs = sum(bug_status.values())
        resolved_bugs = bug_status.get("resolved", 0) + bug_status.get("closed", 0)
        resolution_rate = (resolved_bugs / total_bugs * 100) if total_bugs > 0 else 100.0

        score = (pass_rate * 0.5) + (coverage_pct * 0.3) + (resolution_rate * 0.2)
        return round(score, 1)

    # ── 7. CSV Export Data ────────────────────────────────────────────────────
    def get_runs_for_csv(self, project_id: UUID) -> List[Dict]:
        """Returns all test runs with their result breakdown for CSV export."""
        runs = (
            self.db.query(TestRun)
            .filter(TestRun.project_id == project_id)
            .order_by(TestRun.created_at.desc())
            .all()
        )
        rows = []
        for run in runs:
            items = run.items
            total = len(items)
            passed = sum(1 for i in items if i.result == RunResult.PASSED)
            failed = sum(1 for i in items if i.result == RunResult.FAILED)
            blocked = sum(1 for i in items if i.result == RunResult.BLOCKED)
            skipped = sum(1 for i in items if i.result == RunResult.SKIPPED)
            rows.append({
                "Run Key": run.run_key,
                "Name": run.name,
                "Status": run.status,
                "Environment": run.environment,
                "Total": total,
                "Passed": passed,
                "Failed": failed,
                "Blocked": blocked,
                "Skipped": skipped,
                "Pass Rate %": round((passed / total * 100), 1) if total > 0 else 0,
                "Created At": run.created_at.strftime("%Y-%m-%d %H:%M") if run.created_at else "",
            })
        return rows

    def get_bugs_for_csv(self, project_id: UUID) -> List[Dict]:
        """Returns all bugs for CSV export."""
        bugs = (
            self.db.query(Bug)
            .filter(Bug.project_id == project_id)
            .order_by(Bug.created_at.desc())
            .all()
        )
        rows = []
        for bug in bugs:
            rows.append({
                "Bug Key": bug.bug_key,
                "Title": bug.title,
                "Severity": bug.severity,
                "Priority": bug.priority,
                "Status": bug.status,
                "Environment": bug.environment or "",
                "Browser/OS": bug.browser_os or "",
                "Reported At": bug.reported_at.strftime("%Y-%m-%d %H:%M") if bug.reported_at else "",
                "Resolved At": bug.resolved_at.strftime("%Y-%m-%d %H:%M") if bug.resolved_at else "",
            })
        return rows
