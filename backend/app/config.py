from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://xobalt_user:xobalt_password@localhost:5432/xobalt_db"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Xobalt AI"
    API_V1_PREFIX: str = "/api/v1"

    # LLM Provider — "groq" or "gemini"
    LLM_PROVIDER: str = "groq"

    # Groq (primary)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # Gemini (fallback)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Website Intelligence
    MAX_PAGES_PER_WEBSITE: int = 8
    CRAWL_TIMEOUT: float = 15.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

@lru_cache()
def get_settings() -> Settings:
    return Settings()

