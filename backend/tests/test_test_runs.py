"""
tests/test_test_runs.py
────────────────────────
Integration tests for Phase 6: Test Execution Runs & Results Logging.
7 tests covering: create run, sequential keys, pass result, fail with notes,
auto transition to in_progress, auto transition to completed, tenant isolation.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.test_case import TestCaseCreate
from app.schemas.test_run import RunCreate, RunItemUpdate, RunUpdate
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
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
    """Returns a dict of all services needed by tests."""
    return {
        "auth": AuthService(db),
        "org": OrganizationService(db),
        "proj": ProjectService(db),
        "tc": TestCaseService(db),
        "run": TestRunService(db),
    }


@pytest.fixture
def admin_user(services):
    return services["auth"].user_repo.create(
        UserCreate(
            email="admin@test.com",
            password="Admin@1234",
            full_name="Admin User",
        )
    )


@pytest.fixture
def org(services, admin_user):
    return services["org"].create_organization(
        OrganizationCreate(name="Test Org", description=""),
        admin_user,
    )


@pytest.fixture
def project(services, admin_user, org):
    return services["proj"].create_project(
        org.id,
        ProjectCreate(name="Run Project", key="RUNP", description=""),
        admin_user,
    )


@pytest.fixture
def test_case(services, admin_user, project):
    """Creates one test case to use in runs."""
    return services["tc"].create_case(
        project.id,
        TestCaseCreate(title="Login Test", test_type="manual", priority="high"),
        admin_user,
    )


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_create_run_success(services, admin_user, project, test_case):
    """Creating a run with one test case should produce a planned run with one not_run item."""
    run = services["run"].create_run(
        project.id,
        RunCreate(name="Sprint 1 Run", test_case_ids=[test_case.id]),
        admin_user,
    )
    assert run.name == "Sprint 1 Run"
    assert run.status == "planned"
    assert run.total_count == 1
    assert run.not_run_count == 1
    assert run.passed_count == 0


def test_sequential_run_key(services, admin_user, project, test_case):
    """Two runs for same project should get RUNP-RUN-01 and RUNP-RUN-02."""
    run1 = services["run"].create_run(
        project.id,
        RunCreate(name="Run 1", test_case_ids=[test_case.id]),
        admin_user,
    )
    run2 = services["run"].create_run(
        project.id,
        RunCreate(name="Run 2", test_case_ids=[test_case.id]),
        admin_user,
    )
    assert run1.run_key == "RUNP-RUN-01"
    assert run2.run_key == "RUNP-RUN-02"


def test_submit_pass_result(services, admin_user, project, test_case):
    """Submitting 'passed' should update item and auto-transition run to completed."""
    run = services["run"].create_run(
        project.id,
        RunCreate(name="Pass Run", test_case_ids=[test_case.id]),
        admin_user,
    )
    item_id = run.items[0].id

    result = services["run"].submit_item_result(
        project.id,
        run.id,
        item_id,
        RunItemUpdate(result="passed"),
        admin_user,
    )
    assert result.result == "passed"
    assert result.executed_at is not None

    # Run should auto-complete since all 1 item is now done
    updated_run = services["run"].get_run(project.id, run.id, admin_user)
    assert updated_run.status == "completed"
    assert updated_run.passed_count == 1


def test_submit_fail_requires_notes(services, admin_user, project, test_case):
    """Submitting 'failed' WITHOUT notes should raise 422."""
    run = services["run"].create_run(
        project.id,
        RunCreate(name="Fail Run", test_case_ids=[test_case.id]),
        admin_user,
    )
    item_id = run.items[0].id

    with pytest.raises(HTTPException) as exc_info:
        services["run"].submit_item_result(
            project.id,
            run.id,
            item_id,
            RunItemUpdate(result="failed"),  # no failure_notes
            admin_user,
        )
    assert exc_info.value.status_code == 422


def test_auto_transition_to_in_progress(services, admin_user, project, test_case):
    """Recording any result on a planned run should auto-transition it to in_progress (if items remain)."""
    # Create 2 test cases so the run won't complete after 1 result
    tc2 = services["tc"].create_case(
        project.id,
        TestCaseCreate(title="Logout Test", test_type="manual", priority="medium"),
        admin_user,
    )
    run = services["run"].create_run(
        project.id,
        RunCreate(name="In Progress Run", test_case_ids=[test_case.id, tc2.id]),
        admin_user,
    )
    assert run.status == "planned"

    item_id = run.items[0].id
    services["run"].submit_item_result(
        project.id,
        run.id,
        item_id,
        RunItemUpdate(result="passed"),
        admin_user,
    )

    updated = services["run"].get_run(project.id, run.id, admin_user)
    assert updated.status == "in_progress"


def test_auto_transition_to_completed(services, admin_user, project, test_case):
    """When all items have a result, run should auto-transition to completed."""
    tc2 = services["tc"].create_case(
        project.id,
        TestCaseCreate(title="Signup Test", test_type="manual", priority="low"),
        admin_user,
    )
    run = services["run"].create_run(
        project.id,
        RunCreate(name="Complete Run", test_case_ids=[test_case.id, tc2.id]),
        admin_user,
    )
    for item in run.items:
        services["run"].submit_item_result(
            project.id,
            run.id,
            item.id,
            RunItemUpdate(result="passed"),
            admin_user,
        )

    final = services["run"].get_run(project.id, run.id, admin_user)
    assert final.status == "completed"
    assert final.passed_count == 2
    assert final.not_run_count == 0


def test_tenant_isolation(services, admin_user, project, test_case):
    """A run from project A must not be accessible via project B's URL."""
    # Create a second org + project
    user2 = services["auth"].user_repo.create(
        UserCreate(email="user2@test.com", password="User2@1234", full_name="User Two")
    )
    org2 = services["org"].create_organization(
        OrganizationCreate(name="Org Two", description=""), user2
    )
    proj2 = services["proj"].create_project(
        org2.id,
        ProjectCreate(name="Other Project", key="OTHR", description=""),
        user2,
    )

    run = services["run"].create_run(
        project.id,
        RunCreate(name="Private Run", test_case_ids=[test_case.id]),
        admin_user,
    )

    # user2 trying to access run from project.id — should 403 (not their org)
    with pytest.raises(HTTPException) as exc_info:
        services["run"].get_run(project.id, run.id, user2)
    assert exc_info.value.status_code == 403
