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
    yield
    logger.info(f"Shutting down {settings.APP_NAME}")

app = FastAPI(
    title=settings.APP_NAME,
    version="0.4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

@app.get("/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": "0.4.0"}

