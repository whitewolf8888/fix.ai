"""FastAPI application factory and main entry point."""

import subprocess
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.db.store import BaseStore
from app.models.task import HealthResponse
from app.dependencies import get_task_store, get_settings, get_auth_store, get_analytics_store, get_license_store, get_pilot_store, get_settings_store
from app.api import scan, status as status_api, remediate, webhook, fix, auth, analytics, billing, license, marketing, pilot
from app.api import settings as settings_api
from app.api import enterprise
from app.middleware import rate_limit_middleware, security_headers_middleware, api_rate_limiter
from app.services.auth import get_password_hash
from app.services.license_manager import build_bootstrap_record


# Initialize logging
setup_logging(settings.DEBUG)

# Initialize PostgreSQL database if configured
def init_enterprise_db():
    """Initialize enterprise PostgreSQL database."""
    db_url = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else None
    if db_url and 'postgres' in db_url:
        try:
            from app.db.database import init_db
            init_db()
            logger.info("[DB] PostgreSQL database initialized")
        except Exception as e:
            logger.warning(f"[DB] Could not initialize PostgreSQL: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """App lifespan: startup and shutdown."""
    
    logger.info(f"[App] Starting {settings.APP_NAME} {settings.APP_VERSION}")
    
    # Start rate limiter cleanup task
    import asyncio
    cleanup_task = asyncio.create_task(api_rate_limiter.cleanup_old_entries())
    
    # Startup checks
    if settings.GITHUB_WEBHOOK_SECRET == "local-dev-secret-change-me-in-production":
        logger.warning("[App] Using development webhook secret; set GITHUB_WEBHOOK_SECRET for production")
    
    # Test Semgrep availability
    try:
        result = subprocess.run(["semgrep", "--version"], capture_output=True, timeout=5)
        logger.info(f"[App] Semgrep available: {result.stdout.decode().strip()}")
    except Exception as e:
        logger.warning(f"[App] Semgrep not found: install with `pip install semgrep`")

    # Initialize auth and analytics stores
    auth_store = await get_auth_store()
    await auth_store.init()
    analytics_store = await get_analytics_store()
    await analytics_store.init()

    # Initialize license store
    license_store = await get_license_store()
    await license_store.init()

    pilot_store = await get_pilot_store()
    await pilot_store.init()

    settings_store = await get_settings_store()
    await settings_store.init()

    # Bootstrap admin user if configured
    if settings.BOOTSTRAP_ADMIN_EMAIL and settings.BOOTSTRAP_ADMIN_PASSWORD:
        existing_admin = await auth_store.get_user_by_email(settings.BOOTSTRAP_ADMIN_EMAIL)
        if not existing_admin:
            from app.db.auth_store import UserRecord
            from datetime import datetime

            admin_user = UserRecord(
                user_id="bootstrap-admin",
                email=settings.BOOTSTRAP_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.BOOTSTRAP_ADMIN_PASSWORD),
                role="admin",
                created_at=datetime.utcnow(),
            )
            await auth_store.create_user(admin_user)
            logger.info("[Auth] Bootstrapped admin user")

    if settings.LICENSE_BOOTSTRAP_KEY:
        record = build_bootstrap_record(settings.LICENSE_BOOTSTRAP_KEY, settings.LICENSE_BOOTSTRAP_OWNER)
        await license_store.upsert_license(record)
        logger.info("[License] Bootstrapped license key")
    
    yield
    
    # Cleanup
    cleanup_task.cancel()
    logger.info("[App] Shutting down")


# Create app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise security scanning and AI remediation platform",
    lifespan=lifespan,
)

# Add security middleware
app.middleware("http")(security_headers_middleware)
app.middleware("http")(rate_limit_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(scan.router)
app.include_router(status_api.router)
app.include_router(remediate.router)
app.include_router(webhook.router)
app.include_router(fix.router)
app.include_router(auth.router)
app.include_router(analytics.router)
app.include_router(billing.router)
app.include_router(license.router)
app.include_router(marketing.router)
app.include_router(pilot.router)
app.include_router(settings_api.router)
app.include_router(enterprise.router)


# Health check
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(task_store: BaseStore = Depends(get_task_store)) -> HealthResponse:
    """Health check and configuration status."""
    
    # Check Semgrep
    semgrep_available = False
    try:
        subprocess.run(
            ["semgrep", "--version"],
            capture_output=True,
            timeout=2,
        )
        semgrep_available = True
    except Exception:
        pass
    
    # Check LLM config
    llm_configured = bool(settings.OPENAI_API_KEY or settings.GEMINI_API_KEY)
    llm_provider = settings.LLM_PROVIDER if llm_configured else None
    
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        store_backend=settings.STORE_BACKEND,
        llm_configured=llm_configured,
        llm_provider=llm_provider,
        semgrep_available=semgrep_available,
        github_token_set=bool(settings.GITHUB_TOKEN),
        webhook_secret_set=(settings.GITHUB_WEBHOOK_SECRET != "local-dev-secret-change-me-in-production"),
    )


# Error handlers
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors."""
    return {
        "detail": str(exc),
        "status_code": status.HTTP_400_BAD_REQUEST,
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
