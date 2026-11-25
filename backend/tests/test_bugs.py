"""
tests/test_bugs.py
──────────────────
Integration tests for Phase 7: Bug Tracker & Defect Management.
7 tests covering manual create, create from failed item, sequential keys,
resolve transition, filter queries, deletion, and tenant isolation.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.schemas.bug import BugCreate, BugUpdate
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.test_case import TestCaseCreate
from app.schemas.test_run import RunCreate, RunItemUpdate
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.bug_service import BugService
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService
from app.services.test_case_service import TestCaseService
from app.services.test_run_service import TestRunService

settings.ENVIRONMENT = "testing"

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
def services(db):
    return {
        "auth": AuthService(db),
        "org": OrganizationService(db),
        "proj": ProjectService(db),
        "tc": TestCaseService(db),
        "run": TestRunService(db),
        "bug": BugService(db),
    }


@pytest.fixture
def user(services):
    return services["auth"].user_repo.create(
        UserCreate(email="qa@test.com", password="Password123", full_name="QA Engineer")
    )


@pytest.fixture
def org(services, user):
    return services["org"].create_organization(
        OrganizationCreate(name="QA Org", description=""), user
    )


@pytest.fixture
def project(services, user, org):
    return services["proj"].create_project(
        org.id, ProjectCreate(name="E-Commerce", key="ECOM", description=""), user
    )


@pytest.fixture
def test_case(services, user, project):
    return services["tc"].create_case(
        project.id,
        TestCaseCreate(title="Login Test", test_type="manual", priority="high"),
        user,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_bug_manually(services, user, project, test_case):
    """Can report a new bug manually with severity, priority, and test_case_id."""
    bug = services["bug"].create_bug(
        project.id,
        BugCreate(
            title="Login button unresponsive",
            description="Clicking login does not submit form",
            severity="high",
            priority="critical",
            test_case_id=test_case.id,
        ),
        user,
    )
    assert bug.title == "Login button unresponsive"
    assert bug.bug_key == "ECOM-BUG-01"
    assert bug.status == "open"
    assert bug.severity == "high"
    assert bug.priority == "critical"
    assert bug.test_case_id == test_case.id
    assert bug.tc_key == test_case.tc_key


def test_create_bug_from_failed_run_item(services, user, project, test_case):
    """Can quick-report a bug from a failed test run item."""
    run = services["run"].create_run(
        project.id,
        RunCreate(name="Regression 1", test_case_ids=[test_case.id]),
        user,
    )
    item_id = run.items[0].id
    services["run"].submit_item_result(
        project.id,
        run.id,
        item_id,
        RunItemUpdate(result="failed", failure_notes="Error 500 on submit"),
        user,
    )

    bug = services["bug"].quick_report_from_run_item(
        project.id,
        run.id,
        item_id,
        BugCreate(title="500 Internal Server Error on login"),
        user,
    )
    assert bug.title == "500 Internal Server Error on login"
    assert bug.test_run_item_id == item_id
    assert bug.test_case_id == test_case.id
    assert bug.actual_behavior == "Error 500 on submit"


def test_sequential_bug_key_generation(services, user, project):
    """Subsequent bugs in same project receive sequential keys ECOM-BUG-01, ECOM-BUG-02."""
    b1 = services["bug"].create_bug(
        project.id, BugCreate(title="First bug"), user
    )
    b2 = services["bug"].create_bug(
        project.id, BugCreate(title="Second bug"), user
    )
    assert b1.bug_key == "ECOM-BUG-01"
    assert b2.bug_key == "ECOM-BUG-02"


def test_update_bug_status_to_resolved(services, user, project):
    """When status changes to resolved, resolved_at timestamp must be set."""
    bug = services["bug"].create_bug(
        project.id, BugCreate(title="Checkout bug"), user
    )
    assert bug.resolved_at is None

    updated = services["bug"].update_bug(
        project.id,
        bug.id,
        BugUpdate(status="resolved"),
        user,
    )
    assert updated.status == "resolved"
    assert updated.resolved_at is not None


def test_list_bugs_with_filters(services, user, project):
    """Can filter bugs by status and severity, and get aggregated stats."""
    services["bug"].create_bug(
        project.id, BugCreate(title="Bug 1", severity="critical"), user
    )
    services["bug"].create_bug(
        project.id, BugCreate(title="Bug 2", severity="low"), user
    )

    crit_list = services["bug"].list_bugs(
        project.id, user, severity="critical"
    )
    assert crit_list.total == 1
    assert crit_list.items[0].title == "Bug 1"

    stats = services["bug"].get_stats(project.id, user)
    assert stats.total == 2
    assert stats.open == 2
    assert stats.by_severity["critical"] == 1
    assert stats.by_severity["low"] == 1


def test_delete_bug(services, user, project):
    """Can delete a bug successfully."""
    bug = services["bug"].create_bug(
        project.id, BugCreate(title="Temp bug"), user
    )
    res = services["bug"].delete_bug(project.id, bug.id, user)
    assert "deleted" in res["message"]

    with pytest.raises(HTTPException) as exc:
        services["bug"].get_bug(project.id, bug.id, user)
    assert exc.value.status_code == 404


def test_tenant_isolation_bugs(services, user, project):
    """Users outside organization cannot view or update bugs."""
    other_user = services["auth"].user_repo.create(
        UserCreate(email="intruder@test.com", password="Password123", full_name="Intruder")
    )
    bug = services["bug"].create_bug(
        project.id, BugCreate(title="Confidential defect"), user
    )

    with pytest.raises(HTTPException) as exc:
        services["bug"].get_bug(project.id, bug.id, other_user)
    assert exc.value.status_code == 403
