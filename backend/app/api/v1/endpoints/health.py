"""
app/api/v1/endpoints/health.py
────────────────────────────────
PURPOSE:
  A simple health check endpoint.
  Used by load balancers, Docker, and monitoring systems to verify the
  application is running correctly.

WHY A HEALTH ENDPOINT?
  In production, automated systems (Docker, cloud load balancers, CI/CD)
  periodically call /health to check if the app is alive.
  If it returns 200, the app is healthy. If not, it gets restarted.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", summary="Health Check")
def health_check(db: Session = Depends(get_db)):
    """
    Returns the application status and database connectivity.

    This endpoint:
    1. Confirms the FastAPI app is running.
    2. Attempts a simple database query to verify DB connectivity.
    3. Returns version and environment info.
    """
    db_status = "connected"
    try:
        # Execute a trivial query to verify database connection
        db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "disconnected"

    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
    }

