"""
app/api/v1/router.py
─────────────────────
PURPOSE:
  Central router for all v1 API endpoints.
  Imports and registers individual endpoint routers.

WHY VERSIONING (/api/v1/)?
  When we make breaking changes to the API in the future, we can create
  /api/v2/ while keeping /api/v1/ working for existing clients.
  This is how professional APIs handle backward compatibility.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    auth,
    bugs,
    health,
    organizations,
    projects,
    requirements,
    test_cases,
    test_runs,
    users,
)

# The main v1 router — all routes will be prefixed with /api/v1
api_router = APIRouter()

# Health check — no auth required, used by infra monitoring
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health"],
)

# Authentication — register, login, refresh, logout, /me
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)

# User management — list, get, update, deactivate
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)

# Organizations (Phase 3)
api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["Organizations"],
)

# Projects (Phase 3)
api_router.include_router(
    projects.router,
    prefix="",
    tags=["Projects"],
)

# Requirements & Document Ingestion (Phase 4)
api_router.include_router(
    requirements.router,
    prefix="",
    tags=["Requirements"],
)

# Test Cases & Suites Management (Phase 5)
api_router.include_router(
    test_cases.router,
    prefix="",
    tags=["Test Cases"],
)

# Test Execution Runs & Results (Phase 6)
api_router.include_router(
    test_runs.router,
    prefix="",
    tags=["Test Runs"],
)

# Bug Tracker & Defect Management (Phase 7)
api_router.include_router(
    bugs.router,
    prefix="",
    tags=["Bug Tracker"],
)

# Analytics Dashboard & QA Reports (Phase 8)
api_router.include_router(
    analytics.router,
    prefix="/analytics",
    tags=["Analytics"],
)
