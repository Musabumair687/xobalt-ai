import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config import get_settings
from app.api.hunter import router as hunter_router
from app.api.website_intelligence import router as website_router

settings = get_settings()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode")
    try:
        from app.database.session import init_db
        await init_db()
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
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
app.include_router(hunter_router, prefix="/api/v1")
app.include_router(website_router, prefix="/api/v1")

from app.api.scoring import router as scoring_router
app.include_router(scoring_router, prefix="/api/v1")

from app.api.personalization import router as personalization_router
app.include_router(personalization_router, prefix="/api/v1")

from app.api.campaigns import router as campaigns_router
app.include_router(campaigns_router, prefix="/api/v1")

from app.api.conversations import router as conversations_router
app.include_router(conversations_router, prefix="/api/v1")

from app.api.appointments import router as appointments_router
app.include_router(appointments_router, prefix="/api/v1")

from app.api.leads import router as leads_router
app.include_router(leads_router, prefix="/api/v1")

from app.api.dashboard import router as dashboard_router
app.include_router(dashboard_router, prefix="/api/v1")

from app.api.companies import router as companies_router
app.include_router(companies_router, prefix="/api/v1")

from app.api.analytics import router as analytics_router
app.include_router(analytics_router, prefix="/api/v1")

from app.api.settings import router as settings_router
app.include_router(settings_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.4.0"}

