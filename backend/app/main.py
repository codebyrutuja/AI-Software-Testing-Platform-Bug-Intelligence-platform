"""
app/main.py
────────────
PURPOSE:
  The entry point of the FastAPI application. 
  This is where everything is wired together:
  - App instance created
  - Middleware configured (CORS)
  - Routers registered
  - Startup/shutdown events defined
  - Logging initialized

WHAT IS CORS?
  Cross-Origin Resource Sharing.
  By default, browsers block JavaScript from calling APIs on a different
  domain (or port). Our Angular frontend runs on localhost:4200 but the
  FastAPI backend runs on localhost:8000. Without CORS configuration,
  Angular cannot call the backend.

  We explicitly whitelist the frontend's origin to allow it.

HOW TO RUN:
  cd backend
  uvicorn app.main:app --reload --port 8000

  --reload: Automatically restart when code changes (development only)
  app.main:app means: in the 'app/main.py' file, find the variable 'app'
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.api.v1.router import api_router

# Initialize logging FIRST, before anything else
setup_logging()
logger = logging.getLogger(__name__)


def _seed_superadmin() -> None:
    """
    Create the first platform superadmin if none exists.

    WHY ON STARTUP?
      The very first time the app runs against a fresh database, there are
      no users at all — nobody can register as superadmin through the API
      (the API only creates 'member' role users). So we seed one automatically
      using credentials from the .env file.

    SAFETY:
      - Only runs if NO superadmin exists yet (idempotent — safe to run repeatedly)
      - Logs a warning if default credentials are still in use
      - In production, change FIRST_SUPERADMIN_PASSWORD in .env immediately
    """
    if settings.ENVIRONMENT == "testing":
        return
    try:
        from app.core.database import SessionLocal
        from app.repositories.user_repository import UserRepository
        from app.schemas.user import UserCreate

        db = SessionLocal()
        try:
            repo = UserRepository(db)

            if repo.superadmin_exists():
                logger.info("Superadmin already exists — skipping seed.")
                return

            # Create the first superadmin from .env settings
            superadmin_data = UserCreate(
                email=settings.FIRST_SUPERADMIN_EMAIL,
                full_name=settings.FIRST_SUPERADMIN_NAME,
                password=settings.FIRST_SUPERADMIN_PASSWORD,
            )
            repo.create(superadmin_data, is_superadmin=True)
            logger.info(f"✅ Superadmin created: {settings.FIRST_SUPERADMIN_EMAIL}")

            # Warn if the default password is still set
            if settings.FIRST_SUPERADMIN_PASSWORD in ("Admin@1234", "change-this-password"):
                logger.warning(
                    "⚠️  SECURITY WARNING: Default superadmin password is in use! "
                    "Change FIRST_SUPERADMIN_PASSWORD in your .env file immediately."
                )
        finally:
            db.close()

    except Exception as e:
        # Don't crash the app if seeding fails (e.g., DB not ready yet)
        # The user can create a superadmin manually.
        logger.error(f"Superadmin seed failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager — runs code at startup and shutdown.

    Everything before 'yield' runs at application startup.
    Everything after 'yield' runs at application shutdown.

    This is the modern FastAPI way (replaces @app.on_event("startup")).
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Ensure all tables exist in the database (creates tables if missing)
    if settings.ENVIRONMENT != "testing":
        try:
            from app.core.database import Base, engine
            import app.models  # noqa: F401
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables verified and created.")
        except Exception as e:
            logger.error(f"Error ensuring database tables: {e}")

    # Seed the first superadmin if needed
    _seed_superadmin()

    yield  # Application runs here

    # ── Shutdown ─────────────────────────────────────────────────────────────
    logger.info(f"Shutting down {settings.APP_NAME}")


# ── FastAPI Application Instance ────────────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    ## AI-Powered Software Testing & Bug Intelligence Platform

    A centralized platform for managing the complete QA lifecycle:
    - Test case management
    - Manual test execution
    - Bug tracking and lifecycle management
    - Requirements traceability
    - AI-powered test generation and bug analysis

    **Authentication:** Use the `/api/v1/auth/login` endpoint to get a JWT token,
    then click 'Authorize' and paste it as: `Bearer <your-token>`
    """,
    # Swagger UI available at /docs
    # ReDoc available at /redoc
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────────────────────────
# This MUST be added before registering routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,       # Allow cookies and Authorization headers
    allow_methods=["*"],          # Allow GET, POST, PUT, PATCH, DELETE, OPTIONS
    allow_headers=["*"],          # Allow all headers including Authorization
)

# ── Register API Routes ─────────────────────────────────────────────────────────
# All routes will be prefixed with /api/v1
# Example: /api/v1/health, /api/v1/auth/login, /api/v1/users/
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


# ── Global Exception Handler ────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"},
    )


# ── Root Endpoint ───────────────────────────────────────────────────────────────
@app.get("/", tags=["Root"], summary="API Root")
def root():
    """
    Root endpoint — confirms the API is reachable.
    Not a functional endpoint, just a welcome message.
    """
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
