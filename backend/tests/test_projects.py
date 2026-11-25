"""
tests/test_projects.py
──────────────────────
Integration tests for Phase 3 Project features.
Tests project creation, key validation, duplicate keys, and tenant isolation.
"""
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.models.organization import OrgRole
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService

settings.ENVIRONMENT = "testing"

SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

#Fixtures – preparing the environment and reusable test data
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
def auth_service(db):
    return AuthService(db)


@pytest.fixture
def org_service(db):
    return OrganizationService(db)


@pytest.fixture
def proj_service(db):
    return ProjectService(db)


@pytest.fixture
def user_alice(auth_service):
    return auth_service.user_repo.create(
        UserCreate(email="alice@corp.com", password="Password123", full_name="Alice")
    )


@pytest.fixture
def user_bob(auth_service):
    return auth_service.user_repo.create(
        UserCreate(email="bob@corp.com", password="Password123", full_name="Bob")
    )


@pytest.fixture
def org_alice(org_service, user_alice):
    return org_service.create_organization(OrganizationCreate(name="Alice Corp"), user_alice)


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_create_project_success(proj_service, org_alice, user_alice):
    data = ProjectCreate(name="Mobile App", key="MOB", description="iOS & Android")
    proj = proj_service.create_project(org_alice.id, data, user_alice)

    assert proj.name == "Mobile App"
    assert proj.key == "MOB"
    assert proj.status == "active"
    assert proj.organization_id == org_alice.id


def test_project_key_auto_uppercased(proj_service, org_alice, user_alice):
    data = ProjectCreate(name="Webstore", key="web")
    assert data.key == "WEB"  # Pydantic validator auto-uppercases

    proj = proj_service.create_project(org_alice.id, data, user_alice)
    assert proj.key == "WEB"


def test_invalid_project_key_rejected():
    # Digits and symbols not allowed in project keys
    with pytest.raises(ValidationError):
        ProjectCreate(name="Webstore", key="W123")

    with pytest.raises(ValidationError):
        ProjectCreate(name="Webstore", key="W-1")

    with pytest.raises(ValidationError):
        ProjectCreate(name="Webstore", key="A")  # min 2 chars


def test_duplicate_project_key_rejected(proj_service, org_alice, user_alice):
    proj_service.create_project(org_alice.id, ProjectCreate(name="Payment", key="PAY"), user_alice)

    with pytest.raises(HTTPException) as exc_info:
        proj_service.create_project(org_alice.id, ProjectCreate(name="PayPal", key="PAY"), user_alice)

    assert exc_info.value.status_code == 409
    assert "already exists in this organization" in exc_info.value.detail


def test_same_key_different_org_allowed(proj_service, org_service, org_alice, user_alice, user_bob):
    org_bob = org_service.create_organization(OrganizationCreate(name="Bob Corp"), user_bob)

    # Both orgs can have project key "CORE"
    p1 = proj_service.create_project(org_alice.id, ProjectCreate(name="Core Alice", key="CORE"), user_alice)
    p2 = proj_service.create_project(org_bob.id, ProjectCreate(name="Core Bob", key="CORE"), user_bob)

    assert p1.key == "CORE"
    assert p2.key == "CORE"
    assert p1.organization_id != p2.organization_id


def test_list_projects(proj_service, org_alice, user_alice):
    proj_service.create_project(org_alice.id, ProjectCreate(name="P1", key="ONE"), user_alice)
    proj_service.create_project(org_alice.id, ProjectCreate(name="P2", key="TWO"), user_alice)

    projects = proj_service.list_projects(org_alice.id, user_alice)
    assert len(projects) == 2


def test_archive_project(proj_service, org_alice, user_alice):
    proj = proj_service.create_project(org_alice.id, ProjectCreate(name="P1", key="ONE"), user_alice)

    proj_service.archive_project(proj.id, user_alice)

    # Archived project should no longer appear in active list
    active_projects = proj_service.list_projects(org_alice.id, user_alice)
    assert len(active_projects) == 0


def test_non_member_cannot_access_projects(proj_service, org_alice, user_bob):
    # Bob is NOT a member of org_alice
    with pytest.raises(HTTPException) as exc_info:
        proj_service.list_projects(org_alice.id, user_bob)
    assert exc_info.value.status_code == 403
    assert "not a member" in exc_info.value.detail.lower()
