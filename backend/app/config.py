from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://xobalt_user:xobalt_password@localhost:5432/xobalt_db"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Xobalt AI"
    API_V1_PREFIX: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings() -> Settings:
    return Settings()
