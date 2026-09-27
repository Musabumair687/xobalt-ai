from fastapi import FastAPI
from sqlalchemy import text
from backend.app.config.settings import settings
from backend.app.database.session import engine
from backend.app.database.redis import check_redis_connection

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/")
def read_root():
    return {"message": f"{settings.PROJECT_NAME} operational"}

@app.get("/health")
def health_check():
    # Verify Database Connection
    db_status = "unhealthy"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    # Verify Redis Connection
    redis_status = "healthy" if check_redis_connection() else "unhealthy"

    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "unhealthy"

    return {
        "status": overall_status,
        "database": db_status,
        "redis": redis_status
    }