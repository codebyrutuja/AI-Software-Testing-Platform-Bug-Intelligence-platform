"""
tests/test_organizations.py
────────────────────────────
Integration tests for Phase 3 Organization features.
Tests workspace creation, membership roles, and tenant isolation.
"""
import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base
from app.models.organization import OrgRole
from app.models.user import UserRole
from app.schemas.organization import (
    AddMemberRequest,
    OrganizationCreate,
    OrganizationUpdate,
)
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService

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
def org_service(db):
    return OrganizationService(db)


@pytest.fixture
def auth_service(db):
    return AuthService(db)


@pytest.fixture
def user_alice(auth_service):
    return auth_service.user_repo.create(
        UserCreate(email="alice@acme.com", password="Password123", full_name="Alice")
    )


@pytest.fixture
def user_bob(auth_service):
    return auth_service.user_repo.create(
        UserCreate(email="bob@other.com", password="Password123", full_name="Bob")
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

def test_create_organization_success(org_service, user_alice):
    data = OrganizationCreate(name="Acme Corp", description="QA Workspace")
    org = org_service.create_organization(data, user_alice)

    assert org.name == "Acme Corp"
    assert org.slug == "acme-corp"
    assert org.is_active is True
    assert org.created_by == user_alice.id


def test_creator_becomes_owner(org_service, user_alice):
    data = OrganizationCreate(name="Acme Corp")
    org = org_service.create_organization(data, user_alice)

    members = org_service.get_members(org.id, user_alice)
    assert len(members) == 1
    assert members[0].user_id == user_alice.id
    assert members[0].role == OrgRole.OWNER


def test_list_my_organizations(org_service, user_alice, user_bob):
    # Alice creates Org A
    org_service.create_organization(OrganizationCreate(name="Org Alpha"), user_alice)
    # Bob creates Org B
    org_service.create_organization(OrganizationCreate(name="Org Beta"), user_bob)

    # Alice should only see Org Alpha
    alice_orgs = org_service.get_my_organizations(user_alice)
    assert len(alice_orgs) == 1
    assert alice_orgs[0].name == "Org Alpha"

    # Bob should only see Org Beta
    bob_orgs = org_service.get_my_organizations(user_bob)
    assert len(bob_orgs) == 1
    assert bob_orgs[0].name == "Org Beta"


def test_add_member_as_admin(org_service, user_alice, user_bob):
    org = org_service.create_organization(OrganizationCreate(name="Acme Corp"), user_alice)

    req = AddMemberRequest(email="bob@other.com", role=OrgRole.MEMBER)
    member = org_service.add_member(org.id, req, user_alice)

    assert member.user_id == user_bob.id
    assert member.role == OrgRole.MEMBER

    # Total members should now be 2
    members = org_service.get_members(org.id, user_alice)
    assert len(members) == 2


def test_add_nonexistent_user_fails(org_service, user_alice):
    org = org_service.create_organization(OrganizationCreate(name="Acme Corp"), user_alice)

    req = AddMemberRequest(email="ghost@test.com", role=OrgRole.MEMBER)
    with pytest.raises(HTTPException) as exc_info:
        org_service.add_member(org.id, req, user_alice)
    assert exc_info.value.status_code == 404
    assert "No user found" in exc_info.value.detail


def test_add_duplicate_member_fails(org_service, user_alice, user_bob):
    org = org_service.create_organization(OrganizationCreate(name="Acme Corp"), user_alice)

    # Add Bob once
    req = AddMemberRequest(email="bob@other.com", role=OrgRole.MEMBER)
    org_service.add_member(org.id, req, user_alice)

    # Adding Bob again must fail with 409
    with pytest.raises(HTTPException) as exc_info:
        org_service.add_member(org.id, req, user_alice)
    assert exc_info.value.status_code == 409
    assert "already a member" in exc_info.value.detail


def test_viewer_cannot_add_members(org_service, user_alice, user_bob):
    org = org_service.create_organization(OrganizationCreate(name="Acme Corp"), user_alice)

    # Add Bob as viewer
    org_service.add_member(org.id, AddMemberRequest(email="bob@other.com", role=OrgRole.VIEWER), user_alice)

    # Bob (viewer) tries to add another member -> must be 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        org_service.add_member(org.id, AddMemberRequest(email="charlie@test.com", role=OrgRole.MEMBER), user_bob)
    assert exc_info.value.status_code == 403


def test_tenant_isolation_organization(org_service, user_alice, user_bob):
    # Alice creates Org A
    org_a = org_service.create_organization(OrganizationCreate(name="Org Alpha"), user_alice)

    # Bob (not a member of Org A) tries to view Org A details -> must be 403 Forbidden
    with pytest.raises(HTTPException) as exc_info:
        org_service.get_organization(org_a.id, user_bob)
    assert exc_info.value.status_code == 403
    assert "not a member" in exc_info.value.detail.lower()
