"""
tests/test_analytics.py
────────────────────────
PURPOSE:
  Phase 8 integration tests for Analytics Dashboard & QA Reports.
  7 fast, isolated tests using in-memory SQLite:
    1. Tenant access control verification
    2. Summary counts accuracy (requirements, test cases, runs, bugs)
    3. Requirement coverage percentage and uncovered list
    4. Bug severity breakdown counts
    5. Bug status lifecycle counts
    6. CSV export data generation for test runs
    7. CSV export data generation for bugs
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
settings.ENVIRONMENT = "testing"

from app.core.database import Base
from app.models.bug import Bug, BugSeverity, BugStatus, BugPriority
from app.models.organization import Organization, OrganizationMember
from app.models.project import Project
from app.models.requirement import Requirement, RequirementPriority, RequirementStatus, RequirementCategory
from app.models.test_case import TestCase, TestPriority, TestType, TestStatus
from app.models.test_run import TestRun, TestRunItem, RunEnvironment, RunStatus, RunResult
from app.models.user import User, UserRole
from app.schemas.user import UserCreate
from app.repositories.user_repository import UserRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.organization_repository import OrganizationRepository
from app.api.v1.endpoints.analytics import _get_verified_project
from fastapi import HTTPException

# Avoid pytest trying to collect models as test classes
TestCase.__test__ = False
TestRun.__test__ = False
TestRunItem.__test__ = False

# ── SQLite In-Memory Setup ───────────────────────────────────────────────────
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function", autouse=True)
def db_setup():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def analytics_data(db: Session):
    user_repo = UserRepository(db)
    user = user_repo.create(UserCreate(
        email="analytics@test.com",
        password="Password123",
        full_name="Analytics QA",
        role=UserRole.ADMIN,
    ))

    org = Organization(name="Analytics Org", slug="analytics-org")
    db.add(org)
    db.flush()
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="admin"))

    project = Project(
        organization_id=org.id,
        key="ANLYT",
        name="Analytics Test Project",
        description="For analytics tests",
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    # 2 requirements
    req1 = Requirement(
        project_id=project.id,
        req_key="ANLYT-REQ-01",
        title="Login feature",
        priority=RequirementPriority.HIGH,
        status=RequirementStatus.APPROVED,
        category=RequirementCategory.FUNCTIONAL,
    )
    req2 = Requirement(
        project_id=project.id,
        req_key="ANLYT-REQ-02",
        title="Password reset",
        priority=RequirementPriority.MEDIUM,
        status=RequirementStatus.DRAFT,
        category=RequirementCategory.FUNCTIONAL,
    )
    db.add_all([req1, req2])
    db.flush()

    # 2 test cases (tc1 linked to req1, tc2 unlinked)
    tc1 = TestCase(
        project_id=project.id,
        tc_key="ANLYT-TC-01",
        title="Test Login",
        requirement_id=req1.id,
        priority=TestPriority.HIGH,
        test_type=TestType.MANUAL,
        status=TestStatus.ACTIVE,
    )
    tc2 = TestCase(
        project_id=project.id,
        tc_key="ANLYT-TC-02",
        title="Test Register",
        requirement_id=None,
        priority=TestPriority.MEDIUM,
        test_type=TestType.MANUAL,
        status=TestStatus.ACTIVE,
    )
    db.add_all([tc1, tc2])
    db.flush()

    # 1 test run with 2 items
    run = TestRun(
        project_id=project.id,
        run_key="ANLYT-RUN-01",
        name="Smoke Run",
        status=RunStatus.COMPLETED,
        environment=RunEnvironment.STAGING,
        created_by=user.id,
    )
    db.add(run)
    db.flush()

    item1 = TestRunItem(
        test_run_id=run.id,
        test_case_id=tc1.id,
        result=RunResult.PASSED,
    )
    item2 = TestRunItem(
        test_run_id=run.id,
        test_case_id=tc2.id,
        result=RunResult.FAILED,
        failure_notes="Button unresponsive",
    )
    db.add_all([item1, item2])

    # 2 bugs
    bug1 = Bug(
        project_id=project.id,
        bug_key="ANLYT-BUG-01",
        title="Login crash",
        severity=BugSeverity.CRITICAL,
        priority=BugPriority.CRITICAL,
        status=BugStatus.OPEN,
    )
    bug2 = Bug(
        project_id=project.id,
        bug_key="ANLYT-BUG-02",
        title="Minor styling",
        severity=BugSeverity.LOW,
        priority=BugPriority.LOW,
        status=BugStatus.RESOLVED,
    )
    db.add_all([bug1, bug2])
    db.commit()

    return {
        "user": user,
        "org": org,
        "project": project,
        "req1": req1,
        "req2": req2,
        "tc1": tc1,
        "tc2": tc2,
        "run": run,
        "bug1": bug1,
        "bug2": bug2,
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_tenant_access_control(db: Session, analytics_data):
    """User from another organization cannot access the project analytics"""
    user_repo = UserRepository(db)
    outsider = user_repo.create(UserCreate(
        email="outsider@test.com",
        password="Password123",
        full_name="Outsider",
        role=UserRole.MEMBER,
    ))
    proj_repo = ProjectRepository(db)
    org_repo = OrganizationRepository(db)

    with pytest.raises(HTTPException) as exc_info:
        _get_verified_project(analytics_data["project"].id, outsider, proj_repo, org_repo)
    assert exc_info.value.status_code == 403


def test_project_summary_counts(db: Session, analytics_data):
    """Summary counts correctly aggregate requirements, test cases, runs, and bugs"""
    repo = AnalyticsRepository(db)
    summary = repo.get_project_summary(analytics_data["project"].id)
    assert summary["total_requirements"] == 2
    assert summary["total_test_cases"] == 2
    assert summary["total_test_runs"] == 1
    assert summary["total_bugs"] == 2


def test_requirement_coverage_calculation(db: Session, analytics_data):
    """Requirement coverage calculates covered vs uncovered and coverage percentage"""
    repo = AnalyticsRepository(db)
    coverage = repo.get_requirement_coverage(analytics_data["project"].id)
    assert coverage["covered"] == 1
    assert coverage["uncovered"] == 1
    assert coverage["coverage_percentage"] == 50.0
    assert len(coverage["uncovered_requirements"]) == 1
    assert coverage["uncovered_requirements"][0]["req_key"] == "ANLYT-REQ-02"


def test_bug_severity_breakdown(db: Session, analytics_data):
    """Bug severity aggregates counts correctly per severity enum"""
    repo = AnalyticsRepository(db)
    sev = repo.get_bug_severity_breakdown(analytics_data["project"].id)
    assert sev["critical"] == 1
    assert sev["low"] == 1
    assert sev["high"] == 0
    assert sev["medium"] == 0


def test_bug_status_breakdown(db: Session, analytics_data):
    """Bug status aggregates counts correctly across lifecycle states"""
    repo = AnalyticsRepository(db)
    status_counts = repo.get_bug_status_breakdown(analytics_data["project"].id)
    assert status_counts["open"] == 1
    assert status_counts["resolved"] == 1
    assert status_counts["in_progress"] == 0


def test_runs_csv_export_data(db: Session, analytics_data):
    """Runs CSV export data includes all runs with pass rate and counts"""
    repo = AnalyticsRepository(db)
    rows = repo.get_runs_for_csv(analytics_data["project"].id)
    assert len(rows) == 1
    assert rows[0]["Run Key"] == "ANLYT-RUN-01"
    assert rows[0]["Total"] == 2
    assert rows[0]["Passed"] == 1
    assert rows[0]["Failed"] == 1
    assert rows[0]["Pass Rate %"] == 50.0


def test_bugs_csv_export_data(db: Session, analytics_data):
    """Bugs CSV export data includes all reported defects"""
    repo = AnalyticsRepository(db)
    rows = repo.get_bugs_for_csv(analytics_data["project"].id)
    assert len(rows) == 2
    keys = {r["Bug Key"] for r in rows}
    assert "ANLYT-BUG-01" in keys
    assert "ANLYT-BUG-02" in keys
