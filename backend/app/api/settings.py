"""Settings API — Live System Integrations Status, Verification, and Guardrails."""

from __future__ import annotations

import logging
import time
from typing import Any, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.api.website_intelligence import get_llm
from app.database.dependencies import get_db
from app.models.organization import Organization
from app.models.user import User
from app.auth import get_current_user
from app.services.integration_settings_service import (
    IntegrationSecretError,
    OPTION_FIELDS,
    PROVIDER_FIELDS,
    SECRET_FIELDS,
    decrypt_organization_secrets,
    encrypt_organization_secrets,
    get_organization_runtime_settings,
    load_organization,
    get_organization_settings,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsUpdatePayload(BaseModel):
    require_human_approval: bool
    min_lead_score: int = Field(default=70, ge=0, le=100)
    daily_send_limit: int = Field(default=50, ge=1, le=500)

class IntegrationStatus(BaseModel):
    id: str
    name: str
    type: str
    model: str | None = None
    provider: str
    status: Literal["mock", "configured", "not_configured"]
    credential_source: Literal["organization", "environment", "none"]
    purpose: str


class GuardrailSettings(BaseModel):
    require_human_approval: bool
    min_lead_score: int
    daily_send_limit: int


class SettingsStatusResponse(BaseModel):
    integrations: list[IntegrationStatus]
    status_semantics: dict[str, str]
    guardrails: GuardrailSettings
    integration_config: dict[str, Any]
    available_providers: dict[str, list[str]]
    credential_configured: dict[str, bool]
    can_manage_integrations: bool


class IntegrationSettingsUpdatePayload(BaseModel):
    providers: dict[str, str] = Field(default_factory=dict, max_length=6)
    options: dict[str, str | int] = Field(default_factory=dict, max_length=8)
    secrets: dict[str, str] = Field(default_factory=dict, max_length=10)

    @field_validator("providers")
    @classmethod
    def validate_providers(cls, values: dict[str, str]) -> dict[str, str]:
        for category, provider in values.items():
            if category not in PROVIDER_FIELDS:
                raise ValueError(f"Unsupported integration category: {category}.")
            allowed = PROVIDER_FIELDS[category][1]
            if provider not in allowed:
                raise ValueError(
                    f"Unsupported provider for {category}: {provider}."
                )
        return values

    @field_validator("options")
    @classmethod
    def validate_options(cls, values: dict[str, str | int]) -> dict[str, str | int]:
        unknown = values.keys() - OPTION_FIELDS.keys()
        if unknown:
            raise ValueError(f"Unsupported integration options: {', '.join(sorted(unknown))}.")
        for key, value in values.items():
            if isinstance(value, str) and len(value) > 500:
                raise ValueError(f"{key} must be 500 characters or fewer.")
            if key == "smtp_port" and (
                not isinstance(value, int) or not 1 <= value <= 65535
            ):
                raise ValueError("smtp_port must be between 1 and 65535.")
        return values

    @field_validator("secrets")
    @classmethod
    def validate_secrets(cls, values: dict[str, str]) -> dict[str, str]:
        unknown = values.keys() - SECRET_FIELDS.keys()
        if unknown:
            raise ValueError(f"Unsupported credential fields: {', '.join(sorted(unknown))}.")
        if any(len(value) > 4096 for value in values.values()):
            raise ValueError("Credentials must be 4096 characters or fewer.")
        return values

@router.get(
    "/status",
    response_model=SettingsStatusResponse,
    summary="Get selected provider configuration and organization guardrails",
)
async def get_settings_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsStatusResponse:
    """Report configured provider selection without implying a health check."""
    cfg = get_settings()
    organization = await load_organization(db, current_user.organization_id)
    try:
        effective = get_organization_runtime_settings(organization, cfg)
        organization_secrets = decrypt_organization_secrets(organization)
    except IntegrationSecretError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    saved_guardrails = (organization.settings or {}).get("guardrails", {})

    def credential_source(secret_fields: str | tuple[str, ...]) -> str:
        fields = (secret_fields,) if isinstance(secret_fields, str) else secret_fields
        for name, setting_field in SECRET_FIELDS.items():
            if setting_field in fields and organization_secrets.get(name):
                return "organization"
        if any(getattr(cfg, field, "") for field in fields):
            return "environment"
        return "none"

    def selected_status(
        provider: str,
        required_fields: str | tuple[str, ...] = (),
    ) -> str:
        if provider == "mock":
            return "mock"
        if provider == "auto":
            return "not_configured"
        fields = (required_fields,) if isinstance(required_fields, str) else required_fields
        if fields and not all(getattr(effective, field, "") for field in fields):
            return "not_configured"
        return "configured"

    search_provider = effective.DISCOVERY_PROVIDER.lower()
    if search_provider == "auto":
        search_provider = (
            "serpapi" if effective.SERPAPI_API_KEY
            else "tavily" if effective.TAVILY_API_KEY
            else "auto"
        )
    enrichment_provider = effective.ENRICHMENT_PROVIDER.lower()
    if enrichment_provider == "auto":
        enrichment_provider = (
            "apollo" if effective.APOLLO_API_KEY
            else "hunter" if effective.HUNTER_API_KEY
            else "auto"
        )
    verification_provider = effective.VERIFICATION_PROVIDER.lower()
    if verification_provider == "auto":
        verification_provider = "hunter" if effective.HUNTER_API_KEY else "auto"
    llm_provider = effective.LLM_PROVIDER.lower()
    calendar_provider = effective.CALENDAR_PROVIDER.lower()
    if calendar_provider == "auto":
        has_calendar_credentials = all(
            getattr(effective, field)
            for field in (
                "GOOGLE_CALENDAR_CLIENT_ID",
                "GOOGLE_CALENDAR_CLIENT_SECRET",
                "GOOGLE_CALENDAR_REFRESH_TOKEN",
            )
        )
        calendar_provider = "google" if has_calendar_credentials else "mock"
    email_provider = effective.EMAIL_PROVIDER.lower()
    if email_provider == "auto":
        email_provider = (
            "resend" if effective.RESEND_API_KEY
            else "smtp" if effective.SMTP_USER and effective.SMTP_PASSWORD
            else "auto"
        )
    llm_field = "GEMINI_API_KEY" if llm_provider == "gemini" else "GROQ_API_KEY"
    search_field = "SERPAPI_API_KEY" if search_provider == "serpapi" else "TAVILY_API_KEY"
    enrichment_field = "APOLLO_API_KEY" if enrichment_provider == "apollo" else "HUNTER_API_KEY"
    email_fields = (
        ("SMTP_USER", "SMTP_PASSWORD")
        if email_provider == "smtp"
        else ("RESEND_API_KEY",)
    )
    calendar_fields = (
        "GOOGLE_CALENDAR_CLIENT_ID",
        "GOOGLE_CALENDAR_CLIENT_SECRET",
        "GOOGLE_CALENDAR_REFRESH_TOKEN",
    )

    return SettingsStatusResponse.model_validate({
        "integrations": [
            {
                "id": "llm",
                "name": f"{llm_provider.capitalize()} LLM",
                "type": "LLM",
                "model": effective.GEMINI_MODEL if llm_provider == "gemini" else effective.GROQ_MODEL,
                "provider": llm_provider,
                "status": selected_status(llm_provider, llm_field),
                "credential_source": credential_source(llm_field),
                "purpose": "Company website intelligence extraction, lead scoring, and personalized outreach drafting.",
            },
            {
                "id": "discovery",
                "name": f"{search_provider.capitalize()} discovery",
                "type": "Search & Discovery",
                "provider": search_provider,
                "status": selected_status(
                    search_provider,
                    search_field if search_provider in ("serpapi", "tavily") else (),
                ),
                "credential_source": credential_source(search_field),
                "purpose": "Company discovery provider selected for the lead pipeline.",
            },
            {
                "id": "enrichment",
                "name": f"{enrichment_provider.capitalize()} enrichment",
                "type": "Enrichment",
                "provider": enrichment_provider,
                "status": selected_status(
                    enrichment_provider,
                    enrichment_field if enrichment_provider in ("apollo", "hunter") else (),
                ),
                "credential_source": credential_source(enrichment_field),
                "purpose": "Contact and company enrichment provider selected for the lead pipeline.",
            },
            {
                "id": "verification",
                "name": f"{verification_provider.capitalize()} verification",
                "type": "Email Verification",
                "provider": verification_provider,
                "status": selected_status(
                    verification_provider,
                    "HUNTER_API_KEY" if verification_provider in ("hunter", "auto") else (),
                ),
                "credential_source": credential_source("HUNTER_API_KEY"),
                "purpose": "Email verification provider selected for the lead pipeline.",
            },
            {
                "id": "email",
                "name": f"{email_provider.capitalize()} outbound provider",
                "type": "Email Delivery",
                "provider": email_provider,
                "status": selected_status(
                    email_provider,
                    email_fields if email_provider in ("resend", "smtp") else (),
                ),
                "credential_source": credential_source(email_fields),
                "purpose": "Outbound email provider selected for approved message delivery.",
            },
            {
                "id": "calendar",
                "name": f"{calendar_provider.capitalize()} calendar",
                "type": "Calendar",
                "provider": calendar_provider,
                "status": selected_status(
                    calendar_provider,
                    calendar_fields if calendar_provider == "google" else (),
                ),
                "credential_source": credential_source(calendar_fields),
                "purpose": "Availability lookup and event creation for scheduled appointments.",
            },
        ],
        "status_semantics": {
            "configured": "Provider selection and required configuration are present; connectivity was not checked.",
            "mock": "Explicit mock mode; no real provider calls are made.",
            "not_configured": "Selected provider is missing required configuration.",
        },
        "guardrails": {
            "require_human_approval": saved_guardrails.get("require_human_approval", True),
            "min_lead_score": saved_guardrails.get("min_lead_score", 70),
            "daily_send_limit": saved_guardrails.get("daily_send_limit", 50),
        },
        "integration_config": {
            "providers": {
                "llm": llm_provider,
                "discovery": search_provider,
                "enrichment": enrichment_provider,
                "verification": verification_provider,
                "email": email_provider,
                "calendar": calendar_provider,
            },
            "options": {
                "llm_model": effective.GEMINI_MODEL if llm_provider == "gemini" else effective.GROQ_MODEL,
                "calendar_id": effective.GOOGLE_CALENDAR_ID,
                "resend_from_email": effective.RESEND_FROM_EMAIL,
                "smtp_host": effective.SMTP_HOST,
                "smtp_port": effective.SMTP_PORT,
                "smtp_user": effective.SMTP_USER,
                "smtp_from_email": effective.SMTP_FROM_EMAIL,
                "google_calendar_client_id": effective.GOOGLE_CALENDAR_CLIENT_ID,
            },
        },
        "available_providers": {
            category: sorted(providers)
            for category, (_field, providers) in PROVIDER_FIELDS.items()
        },
        "credential_configured": {
            name: bool(getattr(effective, field, ""))
            for name, field in SECRET_FIELDS.items()
        },
        "can_manage_integrations": current_user.role.lower() in ("owner", "admin"),
    })


@router.put(
    "/integrations",
    response_model=SettingsStatusResponse,
    summary="Save encrypted organization integration settings",
)
async def save_integration_settings(
    payload: IntegrationSettingsUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsStatusResponse:
    if current_user.role.lower() not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and admins can change integrations.",
        )

    organization = await load_organization(db, current_user.organization_id)
    saved_settings = dict(organization.settings or {})
    try:
        secrets = decrypt_organization_secrets(organization)
        for key, value in payload.secrets.items():
            if value:
                secrets[key] = value
            else:
                secrets.pop(key, None)
        encrypted = encrypt_organization_secrets(secrets)
    except IntegrationSecretError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    providers = dict(saved_settings.get("integration_providers", {}))
    providers.update(payload.providers)
    options = dict(saved_settings.get("integration_options", {}))
    options.update(payload.options)
    saved_settings["integration_providers"] = providers
    saved_settings["integration_options"] = options
    if encrypted:
        saved_settings["integration_secrets"] = encrypted
    else:
        saved_settings.pop("integration_secrets", None)
    organization.settings = saved_settings
    await db.commit()
    logger.info("Updated integration configuration for organization %s.", organization.id)
    return await get_settings_status(current_user=current_user, db=db)


@router.post(
    "/save",
    response_model=SettingsStatusResponse,
    summary="Save updated organization guardrail preferences",
)
async def save_settings(
    payload: SettingsUpdatePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SettingsStatusResponse:
    """Persist organization guardrails and return the authoritative settings."""
    result = await db.execute(
        select(Organization).where(
            Organization.id == current_user.organization_id,
        )
    )
    organization = result.scalars().first()
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    settings = dict(organization.settings or {})
    settings["guardrails"] = payload.model_dump()
    organization.settings = settings
    await db.commit()
    logger.info("Updated organization guardrails for %s.", organization.id)
    return await get_settings_status(current_user=current_user, db=db)


@router.post("/test-live", summary="Probe the active LLM and report other provider configuration")
async def test_live_integrations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Probe the active LLM; report configuration only for providers without probes."""
    cfg = await get_organization_settings(db, current_user.organization_id)
    configured = await get_settings_status(current_user, db)
    selected = {item.id: item.model_dump() for item in configured.integrations}
    results: dict[str, dict[str, object]] = {}

    try:
        t0 = time.time()
        llm = get_llm(cfg)
        await llm.ainvoke("Respond with one word: OK")
        llm_ms = int((time.time() - t0) * 1000)
        results[cfg.LLM_PROVIDER] = {
            "status": "operational",
            "connection_tested": True,
            "latency_ms": llm_ms,
            "message": f"LLM probe completed ({llm_ms}ms).",
        }
    except Exception as exc:
        results[cfg.LLM_PROVIDER] = {
            "status": "error",
            "connection_tested": True,
            "message": f"LLM probe failed ({type(exc).__name__}).",
        }

    for key, entry_id in (
        ("discovery", "discovery"),
        ("enrichment", "enrichment"),
        ("verification", "verification"),
        ("email", "email"),
    ):
        entry = selected[entry_id]
        results[key] = {
            "status": entry["status"],
            "provider": entry["provider"],
            "connection_tested": False,
            "message": (
                "Explicit mock mode; no provider connection was attempted."
                if entry["status"] == "mock"
                else "Configuration reported only; provider connectivity was not tested."
            ),
        }

    llm_ok = results.get(cfg.LLM_PROVIDER, {}).get("status") == "operational"

    return {
        "success": llm_ok,
        "connection_tested": [cfg.LLM_PROVIDER],
        "diagnostics": results,
        "summary": (
            "LLM operational; remaining providers report configuration only."
            if llm_ok
            else "LLM connectivity probe failed; other providers report configuration only."
        ),
    }
