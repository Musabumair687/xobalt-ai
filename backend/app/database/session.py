import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import get_settings
from app.database.base import Base
import app.models  # ensure all models are registered on Base

logger = logging.getLogger(__name__)
settings = get_settings()

db_url = settings.DATABASE_URL

if "sqlite" in db_url:
    async_engine = create_async_engine(
        db_url,
        echo=False
    )
else:
    async_engine = create_async_engine(
        db_url,
        pool_size=20,
        max_overflow=10,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def init_db() -> None:
    try:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified and initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        # If PostgreSQL failed, we can inform the user
        raise