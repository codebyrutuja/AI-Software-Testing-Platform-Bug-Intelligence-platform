"""
app/api/v1/endpoints/analytics.py
──────────────────────────────────
PURPOSE:
  Phase 8 — Analytics Dashboard & QA Reports endpoints.

  Routes:
    GET  /api/v1/analytics/dashboard   → Returns full AnalyticsDashboardResponse
    GET  /api/v1/analytics/export/csv  → Returns CSV download (runs or bugs)

  Security:
    Both routes require a valid JWT (get_current_active_user dependency).
    Tenant isolation: validates the project belongs to the user's organisation.
"""
import csv
import io
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    BugSeverityBreakdown,
    BugStatusBreakdown,
    ProjectSummary,
    RequirementCoverage,
    RunPassFailBar,
    UncoveredRequirement,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helper: verify project access ────────────────────────────────────────────
def _get_verified_project(
    project_id: UUID,
    current_user: User,
    project_repo: ProjectRepository,
    org_repo: OrganizationRepository,
):
    """Loads the project and confirms the current user belongs to its organisation."""
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    if not current_user.is_superadmin:
        if not org_repo.is_member(project.organization_id, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project.",
            )
    return project


# ── GET /analytics/dashboard ─────────────────────────────────────────────────
@router.get(
    "/dashboard",
    response_model=AnalyticsDashboardResponse,
    summary="Get analytics dashboard data for a project",
)
def get_analytics_dashboard(
    project_id: UUID = Query(..., description="UUID of the project to analyse"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Returns the full analytics payload for the dashboard:
    - Summary card counts (requirements, test cases, runs, bugs, health score)
    - Last 10 test run pass/fail history bars
    - Bug severity doughnut breakdown
    - Bug status lifecycle counts
    - Requirement traceability coverage (covered / uncovered + uncovered list)
    """
    project_repo = ProjectRepository(db)
    org_repo = OrganizationRepository(db)
    _get_verified_project(project_id, current_user, project_repo, org_repo)

    repo = AnalyticsRepository(db)

    # Gather all data
    summary_counts = repo.get_project_summary(project_id)
    health_score = repo.get_health_score(project_id)
    run_stats = repo.get_test_run_pass_fail_stats(project_id)
    bug_sev = repo.get_bug_severity_breakdown(project_id)
    bug_sta = repo.get_bug_status_breakdown(project_id)
    coverage = repo.get_requirement_coverage(project_id)

    # Build response
    return AnalyticsDashboardResponse(
        summary=ProjectSummary(
            total_requirements=summary_counts["total_requirements"],
            total_test_cases=summary_counts["total_test_cases"],
            total_test_runs=summary_counts["total_test_runs"],
            total_bugs=summary_counts["total_bugs"],
            health_score=health_score,
        ),
        run_history=[
            RunPassFailBar(
                run_key=r["run_key"],
                run_name=r["run_name"],
                status=r["status"],
                environment=r["environment"],
                passed_count=r["passed_count"],
                failed_count=r["failed_count"],
                blocked_count=r["blocked_count"],
                skipped_count=r["skipped_count"],
                not_run_count=r["not_run_count"],
                total_count=r["total_count"],
                pass_rate=r["pass_rate"],
            )
            for r in run_stats
        ],
        bug_severity=BugSeverityBreakdown(
            critical=bug_sev.get("critical", 0),
            high=bug_sev.get("high", 0),
            medium=bug_sev.get("medium", 0),
            low=bug_sev.get("low", 0),
        ),
        bug_status=BugStatusBreakdown(
            open=bug_sta.get("open", 0),
            in_progress=bug_sta.get("in_progress", 0),
            resolved=bug_sta.get("resolved", 0),
            closed=bug_sta.get("closed", 0),
            wont_fix=bug_sta.get("wont_fix", 0),
        ),
        requirement_coverage=RequirementCoverage(
            covered=coverage["covered"],
            uncovered=coverage["uncovered"],
            coverage_percentage=coverage["coverage_percentage"],
            uncovered_requirements=[
                UncoveredRequirement(**r) for r in coverage["uncovered_requirements"]
            ],
        ),
    )


# ── GET /analytics/export/csv ─────────────────────────────────────────────────
@router.get(
    "/export/csv",
    summary="Export project QA data as a CSV file",
)
def export_csv(
    project_id: UUID = Query(..., description="UUID of the project"),
    type: str = Query(..., description="Export type: 'runs' or 'bugs'"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Streams a CSV download of QA data:
    - type=runs → Test run history with pass/fail counts
    - type=bugs → Bug list with severity, priority, status, dates
    """
    if type not in ("runs", "bugs"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid export type. Use 'runs' or 'bugs'.",
        )

    project_repo = ProjectRepository(db)
    org_repo = OrganizationRepository(db)
    project = _get_verified_project(project_id, current_user, project_repo, org_repo)

    repo = AnalyticsRepository(db)

    if type == "runs":
        rows = repo.get_runs_for_csv(project_id)
        filename = f"qa-report-runs-{project.key}.csv"
    else:
        rows = repo.get_bugs_for_csv(project_id)
        filename = f"qa-report-bugs-{project.key}.csv"

    # Build CSV in memory using Python stdlib csv
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("No data found for this project.\n")

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
