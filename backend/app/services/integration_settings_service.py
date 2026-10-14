"""Encrypted, organization-scoped integration configuration."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from typing import Any, AsyncIterator
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import config
from app.config import Settings
from app.models.organization import Organization

PROVIDER_FIELDS = {
    "llm": ("LLM_PROVIDER", {"gemini", "groq"}),
    "discovery": ("DISCOVERY_PROVIDER", {"auto", "mock", "serpapi", "tavily", "ddg"}),
    "enrichment": ("ENRICHMENT_PROVIDER", {"auto", "mock", "apollo", "hunter"}),
    "verification": ("VERIFICATION_PROVIDER", {"auto", "mock", "hunter", "dns"}),
    "email": ("EMAIL_PROVIDER", {"auto", "mock", "resend", "smtp"}),
    "calendar": ("CALENDAR_PROVIDER", {"mock", "google"}),
}

OPTION_FIELDS = {
    "llm_model": (),
    "calendar_id": ("GOOGLE_CALENDAR_ID",),
    "resend_from_email": ("RESEND_FROM_EMAIL",),
    "smtp_host": ("SMTP_HOST",),
    "smtp_port": ("SMTP_PORT",),
    "smtp_user": ("SMTP_USER",),
    "smtp_from_email": ("SMTP_FROM_EMAIL",),
    "google_calendar_client_id": ("GOOGLE_CALENDAR_CLIENT_ID",),
}

SECRET_FIELDS = {
    "gemini_api_key": "GEMINI_API_KEY",
    "groq_api_key": "GROQ_API_KEY",
    "serpapi_api_key": "SERPAPI_API_KEY",
    "tavily_api_key": "TAVILY_API_KEY",
    "apollo_api_key": "APOLLO_API_KEY",
    "hunter_api_key": "HUNTER_API_KEY",
    "resend_api_key": "RESEND_API_KEY",
    "smtp_password": "SMTP_PASSWORD",
    "google_calendar_client_secret": "GOOGLE_CALENDAR_CLIENT_SECRET",
    "google_calendar_refresh_token": "GOOGLE_CALENDAR_REFRESH_TOKEN",
}

_runtime_settings: ContextVar[Settings | None] = ContextVar(
    "xobalt_runtime_settings",
    default=None,
)


def get_settings() -> Settings:
    """Resolve the cached application configuration at the point of use."""
    return config.get_settings()


class IntegrationSecretError(RuntimeError):
    """Raised when encrypted integration credentials cannot be safely read."""


def get_runtime_settings() -> Settings:
    """Return organization-scoped configuration inside a request/task context."""
    return _runtime_settings.get() or get_settings()


def _cipher() -> Fernet:
    key = get_settings().INTEGRATION_ENCRYPTION_KEY
    if not key:
        raise IntegrationSecretError(
            "INTEGRATION_ENCRYPTION_KEY must be configured to save integration credentials."
        )
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise IntegrationSecretError(
            "INTEGRATION_ENCRYPTION_KEY must be a valid Fernet key."
        ) from exc


def decrypt_organization_secrets(organization: Organization) -> dict[str, str]:
    encrypted = (organization.settings or {}).get("integration_secrets")
    if not encrypted:
        return {}
    try:
        plaintext = _cipher().decrypt(encrypted.encode("ascii"))
        result = json.loads(plaintext)
    except (InvalidToken, ValueError, UnicodeEncodeError, json.JSONDecodeError) as exc:
        raise IntegrationSecretError(
            "Stored integration credentials cannot be decrypted; verify the encryption key."
        ) from exc
    if not isinstance(result, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in result.items()
    ):
        raise IntegrationSecretError("Stored integration credentials are invalid.")
    return result


def encrypt_organization_secrets(secrets: dict[str, str]) -> str | None:
    if not secrets:
        return None
    return _cipher().encrypt(
        json.dumps(secrets, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")


def get_organization_runtime_settings(
    organization: Organization,
    base: Settings | None = None,
) -> Settings:
    """Merge organization selections/secrets with environment defaults."""
    effective = base or get_settings()
    saved = organization.settings or {}
    providers = saved.get("integration_providers", {})
    options = saved.get("integration_options", {})
    secrets = decrypt_organization_secrets(organization)
    updates: dict[str, Any] = {}

    if isinstance(providers, dict):
        for _category, (field, allowed) in PROVIDER_FIELDS.items():
            value = providers.get(_category)
            if isinstance(value, str) and value in allowed:
                updates[field] = value

    if isinstance(options, dict):
        for option, fields in OPTION_FIELDS.items():
            if option == "llm_model":
                continue
            value = options.get(option)
            if value is not None:
                for field in fields:
                    updates[field] = value
        model = options.get("llm_model")
        if model is not None:
            llm_provider = (
                providers.get("llm")
                if isinstance(providers, dict)
                else None
            )
            if llm_provider not in {"gemini", "groq"}:
                llm_provider = effective.LLM_PROVIDER
            model_field = (
                "GEMINI_MODEL" if llm_provider == "gemini" else "GROQ_MODEL"
            )
            updates[model_field] = model

    for key, field in SECRET_FIELDS.items():
        if key in secrets:
            updates[field] = secrets[key]

    return effective.model_copy(update=updates)


async def load_organization(
    db: AsyncSession,
    organization_id: UUID,
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.id == organization_id)
    )
    organization = result.scalars().first()
    if organization is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )
    return organization


async def get_organization_settings(
    db: AsyncSession,
    organization_id: UUID,
) -> Settings:
    organization = await load_organization(db, organization_id)
    try:
        return get_organization_runtime_settings(organization)
    except IntegrationSecretError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@asynccontextmanager
async def organization_settings_scope(
    db: AsyncSession,
    organization_id: UUID,
) -> AsyncIterator[Settings]:
    effective = await get_organization_settings(db, organization_id)
    token: Token[Settings | None] = _runtime_settings.set(effective)
    try:
        yield effective
    finally:
        _runtime_settings.reset(token)
