"""
tests/test_auth.py
───────────────────
PURPOSE:
  Integration tests for the authentication API endpoints.
  Uses FastAPI's TestClient to simulate real HTTP requests
  without needing a running server.

HOW IT WORKS:
  - Uses an in-memory SQLite database (not PostgreSQL) for speed.
  - Each test gets a fresh database via the `db_session` fixture.
  - The `client` fixture overrides the `get_db` dependency to use the test DB.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
settings.ENVIRONMENT = "testing"

from app.core.database import Base, get_db
from app.main import app

# ── Test Database Setup ──────────────────────────────────────────────────────────
# Use SQLite in-memory for tests — fast, no setup required, isolated
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite + pytest
    poolclass=StaticPool,  # Reuse single connection (in-memory DB would be lost otherwise)
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="function", autouse=True)
def db_setup():
    """Create all tables before each test, drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    """Provide a fresh database session for each test."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """
    FastAPI TestClient with the real `get_db` dependency overridden
    to use the test SQLite database.
    """
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Helper ───────────────────────────────────────────────────────────────────────

def register_user(client, email="test@example.com", password="Test1234", full_name="Test User"):
    """Helper to register a test user."""
    return client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "full_name": full_name,
    })


# ── Registration Tests ────────────────────────────────────────────────────────────

def test_register_success(client):
    """A new user can register successfully."""
    response = register_user(client)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["role"] == "member"
    assert data["is_active"] is True
    assert data["is_superadmin"] is False
    assert "hashed_password" not in data   # Must never be exposed


def test_register_duplicate_email(client):
    """Registering with an already-used email returns 409 Conflict."""
    register_user(client)   # First registration
    response = register_user(client)   # Duplicate
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_register_weak_password(client):
    """Registration with a weak password (no uppercase) returns 422."""
    response = client.post("/api/v1/auth/register", json={
        "email": "weak@example.com",
        "password": "password1",   # No uppercase letter
        "full_name": "Weak User",
    })
    assert response.status_code == 422


def test_register_short_password(client):
    """Registration with password shorter than 8 chars returns 422."""
    response = client.post("/api/v1/auth/register", json={
        "email": "short@example.com",
        "password": "Ab1",   # Too short
    })
    assert response.status_code == 422


# ── Login Tests ───────────────────────────────────────────────────────────────────

def test_login_success(client):
    """Valid credentials return access + refresh tokens."""
    register_user(client)
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_wrong_password(client):
    """Wrong password returns 401 with a generic error message."""
    register_user(client)
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPass1",
    })
    assert response.status_code == 401
    assert "Invalid" in response.json()["detail"]


def test_login_nonexistent_email(client):
    """Login with unknown email returns 401 (not 404 — prevents enumeration)."""
    response = client.post("/api/v1/auth/login", json={
        "email": "nobody@example.com",
        "password": "Test1234",
    })
    assert response.status_code == 401


# ── Token / Me Tests ──────────────────────────────────────────────────────────────

def test_get_me_with_valid_token(client):
    """GET /auth/me with a valid token returns the current user."""
    register_user(client)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    token = login_resp.json()["access_token"]

    me_resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "test@example.com"


def test_get_me_without_token(client):
    """GET /auth/me without a token returns 403."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 403


def test_get_me_with_invalid_token(client):
    """GET /auth/me with a garbage token returns 403."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not_a_real_token"},
    )
    assert response.status_code == 403


# ── Token Refresh Tests ───────────────────────────────────────────────────────────

def test_refresh_token(client):
    """A valid refresh token returns new access + refresh tokens."""
    register_user(client)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()


def test_refresh_with_access_token_fails(client):
    """Using an access token as a refresh token is rejected."""
    register_user(client)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    access_token = login_resp.json()["access_token"]  # Wrong token type

    refresh_resp = client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token,  # Access token used as refresh — should fail
    })
    assert refresh_resp.status_code == 401


# ── Change Password Tests ─────────────────────────────────────────────────────────

def test_change_password(client):
    """A user can change their password with the correct current password."""
    register_user(client)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    token = login_resp.json()["access_token"]
    user_id = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).json()["id"]

    change_resp = client.post(
        f"/api/v1/users/{user_id}/change-password",
        json={"current_password": "Test1234", "new_password": "NewPass5678"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert change_resp.status_code == 200
    assert "successfully" in change_resp.json()["message"]

    # Verify old password no longer works
    old_login = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "Test1234",
    })
    assert old_login.status_code == 401

    # Verify new password works
    new_login = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "NewPass5678",
    })
    assert new_login.status_code == 200
