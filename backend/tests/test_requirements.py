"""
tests/test_requirements.py
──────────────────────────
Integration tests for Phase 4: Requirements Ingestion & Parsing Engine.
Tests document parsing, sequential keys, criteria management, and tenant isolation.
"""
import io
import pytest
from fastapi import HTTPException, UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.schemas.organization import OrganizationCreate
from app.schemas.project import ProjectCreate
from app.schemas.requirement import RequirementCreate, RequirementUpdate
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService

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
def auth_service(db):
    return AuthService(db)


@pytest.fixture
def org_service(db):
    return OrganizationService(db)


@pytest.fixture
def proj_service(db):
    return ProjectService(db)


@pytest.fixture
def req_service(db):
    return RequirementService(db)


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
def project_alice(org_service, proj_service, user_alice):
    org = org_service.create_organization(OrganizationCreate(name="Alice Corp"), user_alice)
    return proj_service.create_project(
        org.id, ProjectCreate(name="E-Commerce", key="ECOM"), user_alice
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_manual_create_requirement(req_service, project_alice, user_alice):
    data = RequirementCreate(
        title="User Login via Email & Password",
        description="Users should be able to authenticate with email and password.",
        category="security",
        priority="high",
        status="approved",
        acceptance_criteria=[
            "Given valid credentials, return 200 with JWT access token.",
            "Given invalid password, return 401 with error message.",
        ],
    )
    req = req_service.create_requirement(project_alice.id, data, user_alice)

    assert req.title == "User Login via Email & Password"
    assert req.req_key == "ECOM-REQ-01"
    assert req.category == "security"
    assert req.priority == "high"
    assert req.status == "approved"
    assert len(req.acceptance_criteria) == 2
    assert "JWT access token" in req.acceptance_criteria[0].criteria


def test_sequential_req_key_generation(req_service, project_alice, user_alice):
    req1 = req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="Feature 1", acceptance_criteria=["Check 1"]),
        user_alice,
    )
    req2 = req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="Feature 2", acceptance_criteria=["Check 2"]),
        user_alice,
    )

    assert req1.req_key == "ECOM-REQ-01"
    assert req2.req_key == "ECOM-REQ-02"


def test_get_and_update_requirement(req_service, project_alice, user_alice):
    created = req_service.create_requirement(
        project_alice.id,
        RequirementCreate(
            title="Initial Title",
            description="Initial Description",
            acceptance_criteria=["Criterion 1"],
        ),
        user_alice,
    )

    updated = req_service.update_requirement(
        project_alice.id,
        created.id,
        RequirementUpdate(
            title="Updated Title",
            priority="critical",
            acceptance_criteria=["New Criterion 1", "New Criterion 2"],
        ),
        user_alice,
    )

    assert updated.title == "Updated Title"
    assert updated.priority == "critical"
    assert len(updated.acceptance_criteria) == 2
    assert updated.acceptance_criteria[0].criteria == "New Criterion 1"


def test_delete_requirement(req_service, project_alice, user_alice):
    req = req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="To be deleted", acceptance_criteria=["Check"]),
        user_alice,
    )

    res = req_service.delete_requirement(project_alice.id, req.id, user_alice)
    assert res["message"] == "Requirement deleted successfully."

    with pytest.raises(HTTPException) as exc_info:
        req_service.get_requirement(project_alice.id, req.id, user_alice)
    assert exc_info.value.status_code == 404


def test_list_requirements_filters_and_search(req_service, project_alice, user_alice):
    req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="User Checkout Flow", category="functional", priority="high"),
        user_alice,
    )
    req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="Payment Gateway Integration", category="security", priority="critical"),
        user_alice,
    )
    req_service.create_requirement(
        project_alice.id,
        RequirementCreate(title="Product Search UI", category="ui_ux", priority="low"),
        user_alice,
    )

    # Filter by category
    security_reqs = req_service.list_requirements(project_alice.id, user_alice, category="security")
    assert security_reqs.total == 1
    assert security_reqs.items[0].title == "Payment Gateway Integration"

    # Filter by search
    search_reqs = req_service.list_requirements(project_alice.id, user_alice, search="Checkout")
    assert search_reqs.total == 1
    assert search_reqs.items[0].title == "User Checkout Flow"


def test_markdown_document_upload_and_parsing(req_service, project_alice, user_alice):
    md_content = """# Authentication & Authorization

## User Registration
As a new user, I want to create an account so that I can access the system.
Acceptance Criteria:
- Must validate email format
- Password minimum 8 characters with digit and uppercase
- Returns 201 on success

## Two-Factor Authentication
Given a user with 2FA enabled, when they enter password, then prompt for 6-digit OTP code.
"""
    file_bytes = md_content.encode("utf-8")
    upload_file = UploadFile(
        file=io.BytesIO(file_bytes),
        filename="auth_spec.md",
    )

    result = req_service.upload_and_parse_document(
        project_alice.id, upload_file, user_alice
    )

    assert result.extracted_count >= 2
    assert result.document.parsing_status == "parsed"
    assert result.document.filename == "auth_spec.md"

    # Verify requirements created in DB
    all_reqs = req_service.list_requirements(project_alice.id, user_alice)
    assert all_reqs.total >= 2


def test_tenant_isolation_requirements(org_service, proj_service, req_service, user_alice, user_bob):
    org_bob = org_service.create_organization(OrganizationCreate(name="Bob Corp"), user_bob)
    proj_bob = proj_service.create_project(
        org_bob.id, ProjectCreate(name="Bob App", key="BOB"), user_bob
    )

    req_service.create_requirement(
        proj_bob.id,
        RequirementCreate(title="Bob Secret Feature"),
        user_bob,
    )

    # Alice (from another org) cannot read Bob's requirements
    with pytest.raises(HTTPException) as exc_info:
        req_service.list_requirements(proj_bob.id, user_alice)
    assert exc_info.value.status_code == 403


def test_empty_file_rejected(req_service, project_alice, user_alice):
    upload_file = UploadFile(
        file=io.BytesIO(b""),
        filename="empty.md",
    )
    with pytest.raises(HTTPException) as exc_info:
        req_service.upload_and_parse_document(project_alice.id, upload_file, user_alice)
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()
