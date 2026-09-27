from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Xobalt AI Platform"
    DATABASE_URL: str = "postgresql+psycopg2://xobalt_user:xobalt_password@127.0.0.1:5432/xobalt_db"
    REDIS_URL: str = "redis://127.0.0.1:6379/0"

    class Config:
        env_file = ".env"

settings = Settings()