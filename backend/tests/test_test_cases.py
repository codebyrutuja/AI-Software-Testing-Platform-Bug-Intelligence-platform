"""
tests/test_test_cases.py
────────────────────────
Integration tests for Phase 5: Test Cases & Suites Management.
Tests suite hierarchy, step procedures, sequential keys, requirement linking, and tenant isolation.
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
from app.schemas.requirement import RequirementCreate
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseUpdate,
    TestStepCreate,
    TestSuiteCreate,
)
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.services.organization_service import OrganizationService
from app.services.project_service import ProjectService
from app.services.requirement_service import RequirementService
from app.services.test_case_service import TestCaseService

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
def tc_service(db):
    return TestCaseService(db)


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

def test_create_test_suite_and_sub_suite(tc_service, project_alice, user_alice):
    parent = tc_service.create_suite(
        project_alice.id,
        TestSuiteCreate(name="Authentication", description="Auth tests"),
        user_alice,
    )
    assert parent.name == "Authentication"
    assert parent.project_id == project_alice.id
    assert parent.case_count == 0

    sub = tc_service.create_suite(
        project_alice.id,
        TestSuiteCreate(
            name="OAuth & SSO",
            description="Third party providers",
            parent_suite_id=parent.id,
        ),
        user_alice,
    )
    assert sub.parent_suite_id == parent.id

    suites = tc_service.list_suites(project_alice.id, user_alice)
    assert len(suites) == 2


def test_create_test_case_with_steps_and_key(tc_service, project_alice, user_alice):
    suite = tc_service.create_suite(
        project_alice.id, TestSuiteCreate(name="Cart"), user_alice
    )

    data = TestCaseCreate(
        title="Add Item to Shopping Cart",
        suite_id=suite.id,
        description="Verify user can add a product to cart.",
        preconditions="User must be on product detail page.",
        test_type="regression",
        priority="high",
        status="active",
        estimated_duration_minutes=3,
        steps=[
            TestStepCreate(
                step_number=1,
                action="Click 'Add to Cart' button",
                test_data="Product ID: SKU-100",
                expected_result="Cart counter increments by 1.",
            ),
            TestStepCreate(
                step_number=2,
                action="Navigate to /cart",
                expected_result="Item SKU-100 appears in list with quantity 1.",
            ),
        ],
    )

    tc1 = tc_service.create_case(project_alice.id, data, user_alice)
    assert tc1.tc_key == "ECOM-TC-01"
    assert tc1.title == "Add Item to Shopping Cart"
    assert tc1.suite_name == "Cart"
    assert len(tc1.steps) == 2
    assert tc1.steps[0].step_number == 1
    assert tc1.steps[0].action == "Click 'Add to Cart' button"

    # Second test case auto-increments key
    data2 = TestCaseCreate(title="Remove Item from Cart", suite_id=suite.id)
    tc2 = tc_service.create_case(project_alice.id, data2, user_alice)
    assert tc2.tc_key == "ECOM-TC-02"


def test_link_test_case_to_requirement(req_service, tc_service, project_alice, user_alice):
    # Create Phase 4 Requirement
    req = req_service.create_requirement(
        project_alice.id,
        RequirementCreate(
            title="User Checkout Flow",
            category="functional",
            priority="high",
            acceptance_criteria=["Order total must calculate sales tax."],
        ),
        user_alice,
    )

    # Create Phase 5 Test Case linked to Requirement
    tc = tc_service.create_case(
        project_alice.id,
        TestCaseCreate(
            title="Verify Tax Calculation on Checkout",
            requirement_id=req.id,
            steps=[
                TestStepCreate(
                    step_number=1,
                    action="Proceed to checkout with $100 cart",
                    expected_result="Tax line item displays $8.25.",
                )
            ],
        ),
        user_alice,
    )

    assert tc.requirement_id == req.id
    assert tc.requirement_key == req.req_key
    assert tc.requirement_title == "User Checkout Flow"


def test_update_test_case_and_replace_steps(tc_service, project_alice, user_alice):
    created = tc_service.create_case(
        project_alice.id,
        TestCaseCreate(
            title="Initial Title",
            priority="low",
            steps=[
                TestStepCreate(step_number=1, action="Step 1", expected_result="Result 1")
            ],
        ),
        user_alice,
    )

    updated = tc_service.update_case(
        project_alice.id,
        created.id,
        TestCaseUpdate(
            title="Updated Title",
            priority="critical",
            steps=[
                TestStepCreate(step_number=1, action="New Step 1", expected_result="New Result 1"),
                TestStepCreate(step_number=2, action="New Step 2", expected_result="New Result 2"),
            ],
        ),
        user_alice,
    )

    assert updated.title == "Updated Title"
    assert updated.priority == "critical"
    assert len(updated.steps) == 2
    assert updated.steps[1].action == "New Step 2"


def test_delete_test_case(tc_service, project_alice, user_alice):
    tc = tc_service.create_case(
        project_alice.id,
        TestCaseCreate(title="Temporary Test Case"),
        user_alice,
    )

    res = tc_service.delete_case(project_alice.id, tc.id, user_alice)
    assert res["message"] == "Test case deleted successfully."

    with pytest.raises(HTTPException) as exc_info:
        tc_service.get_case(project_alice.id, tc.id, user_alice)
    assert exc_info.value.status_code == 404


def test_list_test_cases_filtering(tc_service, project_alice, user_alice):
    suite_auth = tc_service.create_suite(
        project_alice.id, TestSuiteCreate(name="Auth"), user_alice
    )
    suite_pay = tc_service.create_suite(
        project_alice.id, TestSuiteCreate(name="Pay"), user_alice
    )

    tc_service.create_case(
        project_alice.id,
        TestCaseCreate(title="Login Test", suite_id=suite_auth.id, priority="high", test_type="smoke"),
        user_alice,
    )
    tc_service.create_case(
        project_alice.id,
        TestCaseCreate(title="Stripe Payment Test", suite_id=suite_pay.id, priority="critical", test_type="regression"),
        user_alice,
    )

    # Filter by suite
    res_suite = tc_service.list_cases(project_alice.id, user_alice, suite_id=suite_auth.id)
    assert res_suite.total == 1
    assert res_suite.items[0].title == "Login Test"

    # Filter by search
    res_search = tc_service.list_cases(project_alice.id, user_alice, search="Stripe")
    assert res_search.total == 1
    assert res_search.items[0].title == "Stripe Payment Test"


def test_tenant_isolation_test_cases(org_service, proj_service, tc_service, user_alice, user_bob):
    org_bob = org_service.create_organization(OrganizationCreate(name="Bob Corp"), user_bob)
    proj_bob = proj_service.create_project(
        org_bob.id, ProjectCreate(name="Bob App", key="BOB"), user_bob
    )

    tc_service.create_case(
        proj_bob.id,
        TestCaseCreate(title="Secret Bob Test"),
        user_bob,
    )

    # Alice from another organization cannot list or view Bob's test cases
    with pytest.raises(HTTPException) as exc_info:
        tc_service.list_cases(proj_bob.id, user_alice)
    assert exc_info.value.status_code == 403
