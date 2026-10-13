from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./xobalt.db"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    APP_NAME: str = "Xobalt AI"
    API_V1_PREFIX: str = "/api/v1"

    # LLM Provider — "groq" or "gemini"
    LLM_PROVIDER: str = "gemini"

    # Groq (primary)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    # Gemini (fallback)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # Website Intelligence
    MAX_PAGES_PER_WEBSITE: int = 8
    CRAWL_TIMEOUT: float = 15.0

    # Search & Discovery (SerpAPI, Tavily, DuckDuckGo)
    DISCOVERY_PROVIDER: str = "auto"  # "serpapi", "tavily", "ddg", or "mock"
    SERPAPI_API_KEY: str = ""
    TAVILY_API_KEY: str = ""

    # Contact Enrichment (Apollo.io, Hunter.io)
    ENRICHMENT_PROVIDER: str = "auto"  # "apollo", "hunter", or "mock"
    APOLLO_API_KEY: str = ""
    HUNTER_API_KEY: str = ""

    # Contact Verification (Hunter, DNS MX, Mock)
    VERIFICATION_PROVIDER: str = "auto"  # "hunter", "dns", or "mock"

    # Email Outreach (Resend, SMTP, Mock)
    EMAIL_PROVIDER: str = "auto"  # "resend", "smtp", or "mock"
    RESEND_API_KEY: str = ""
    RESEND_FROM_EMAIL: str = "onboarding@resend.dev"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""

    # Calendar (Google Calendar)
    CALENDAR_PROVIDER: str = "auto"  # "google" or "mock"
    GOOGLE_CALENDAR_CLIENT_ID: str = ""
    GOOGLE_CALENDAR_CLIENT_SECRET: str = ""
    GOOGLE_CALENDAR_REFRESH_TOKEN: str = ""
    GOOGLE_CALENDAR_ID: str = "primary"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

@lru_cache()
def get_settings() -> Settings:
    return Settings()

