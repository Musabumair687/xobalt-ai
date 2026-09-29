import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import get_settings
from app.database.base import Base
import app.models  # Ensures all models are loaded

async def reset_database():
    print("Connecting to database...")
    settings = get_settings()
    engine = create_async_engine(settings.DATABASE_URL)
    
    print("Dropping all existing tables...")
    async with engine.begin() as conn:
        # Drop alembic_version manually if it exists
        await conn.run_sync(lambda sync_conn: sync_conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version;"))
        await conn.run_sync(Base.metadata.drop_all)
        
    print("Database reset complete. You can now run migrations.")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(reset_database())
