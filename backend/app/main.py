import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from contextlib import asynccontextmanager
from fastapi import Depends, HTTPException, status
from sqlalchemy import text
from app.config import get_settings
from app.auth import get_current_user
from app.database.redis import check_redis_connection
from app.database.session import AsyncSessionLocal
from app.workers.celery_app import check_worker_connection
from app.api.auth import router as auth_router
from app.api.hunter import router as hunter_router
from app.api.website_intelligence import router as website_router

settings = get_settings()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1")
protected_dependencies = [Depends(get_current_user)]
app.include_router(hunter_router, prefix="/api/v1", dependencies=protected_dependencies)
app.include_router(website_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.scoring import router as scoring_router
app.include_router(scoring_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.personalization import router as personalization_router
app.include_router(personalization_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.campaigns import router as campaigns_router
app.include_router(campaigns_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.conversations import router as conversations_router
app.include_router(conversations_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.appointments import router as appointments_router
app.include_router(appointments_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.leads import router as leads_router
app.include_router(leads_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.companies import router as companies_router
app.include_router(companies_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1", dependencies=protected_dependencies)

from app.api.settings import router as settings_router
app.include_router(settings_router, prefix="/api/v1", dependencies=protected_dependencies)


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.4.0"}


async def database_ready() -> bool:
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.warning("Database readiness check failed (%s).", type(exc).__name__)
        return False


@app.get("/ready", summary="Check database, queue broker, and worker readiness")
async def readiness_check():
    db_ok, broker_ok = await asyncio.gather(
        database_ready(),
        asyncio.to_thread(check_redis_connection),
    )
    worker_ok = (
        await asyncio.to_thread(check_worker_connection)
        if broker_ok
        else False
    )
    checks = {
        "database": "available" if db_ok else "unavailable",
        "queue_broker": "available" if broker_ok else "unavailable",
        "worker": "available" if worker_ok else "unavailable",
    }
    if not all((db_ok, broker_ok, worker_ok)):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}
