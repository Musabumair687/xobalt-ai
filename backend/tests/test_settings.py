import json
import uuid
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app.api import settings as settings_api
from app.config import Settings
from app.models.organization import Organization
from app.models.user import User
from app.services import integration_settings_service
from app.services.integration_settings_service import get_organization_runtime_settings


async def create_settings_user(async_session):
    organization = Organization(
        name="Settings Organization",
        slug=f"settings-{uuid.uuid4().hex}",
    )
    async_session.add(organization)
    await async_session.flush()
    user = User(
        organization_id=organization.id,
        email=f"{organization.id}@example.test",
        full_name="Settings User",
        role="owner",
    )
    async_session.add(user)
    await async_session.commit()
    return user


def test_settings_environment_file_is_backend_scoped():
    expected_env_file = Path(__file__).resolve().parents[1] / ".env"

    assert Settings.model_config["env_file"] == expected_env_file


@pytest.mark.asyncio
async def test_settings_status_does_not_expose_provider_keys(
    async_session,
    monkeypatch,
):
    secret_values = {
        "GEMINI_API_KEY": "test-gemini-secret",
        "TAVILY_API_KEY": "test-tavily-secret",
        "APOLLO_API_KEY": "test-apollo-secret",
        "RESEND_API_KEY": "test-resend-secret",
    }
    config = Settings(**secret_values)
    monkeypatch.setattr(settings_api, "get_settings", lambda: config)
    user = await create_settings_user(async_session)

    result = await settings_api.get_settings_status(user, async_session)
    serialized = json.dumps(result.model_dump())

    for secret in secret_values.values():
        assert secret not in serialized
    assert all(
        "masked_key" not in integration.model_dump()
        for integration in result.integrations
    )
    assert all(
        integration.status != "connected"
        for integration in result.integrations
    )


@pytest.mark.asyncio
async def test_mock_selection_wins_over_present_provider_keys(
    async_session,
    monkeypatch,
):
    config = Settings(
        DISCOVERY_PROVIDER="mock",
        TAVILY_API_KEY="unused-tavily-key",
        ENRICHMENT_PROVIDER="mock",
        APOLLO_API_KEY="unused-apollo-key",
        VERIFICATION_PROVIDER="mock",
    )
    monkeypatch.setattr(settings_api, "get_settings", lambda: config)
    user = await create_settings_user(async_session)

    result = await settings_api.get_settings_status(user, async_session)
    providers = {item.id: item for item in result.integrations}

    assert providers["discovery"].status == "mock"
    assert providers["enrichment"].status == "mock"
    assert providers["verification"].status == "mock"


@pytest.mark.asyncio
async def test_guardrail_settings_persist_and_are_returned(
    async_session,
    monkeypatch,
):
    monkeypatch.setattr(settings_api, "get_settings", lambda: Settings())
    user = await create_settings_user(async_session)
    payload = settings_api.SettingsUpdatePayload(
        require_human_approval=False,
        min_lead_score=82,
        daily_send_limit=17,
    )

    result = await settings_api.save_settings(payload, user, async_session)
    reread = await settings_api.get_settings_status(user, async_session)

    assert result.guardrails.require_human_approval is False
    assert result.guardrails.min_lead_score == 82
    assert result.guardrails.daily_send_limit == 17
    assert reread.guardrails == result.guardrails


@pytest.mark.asyncio
async def test_integration_credentials_are_encrypted_and_applied_per_organization(
    async_session,
    monkeypatch,
):
    encryption_key = Fernet.generate_key().decode("ascii")
    config = Settings(
        INTEGRATION_ENCRYPTION_KEY=encryption_key,
        GROQ_MODEL="groq-model-unchanged",
    )
    monkeypatch.setattr(settings_api, "get_settings", lambda: config)
    monkeypatch.setattr(integration_settings_service, "get_settings", lambda: config)
    user = await create_settings_user(async_session)

    result = await settings_api.save_integration_settings(
        settings_api.IntegrationSettingsUpdatePayload(
            providers={
                "llm": "gemini",
                "discovery": "tavily",
                "calendar": "google",
            },
            options={
                "llm_model": "gemini-test-model",
                "google_calendar_client_id": "oauth-client-id",
            },
            secrets={
                "gemini_api_key": "organization-gemini-secret",
                "tavily_api_key": "organization-tavily-secret",
                "google_calendar_client_secret": "calendar-client-secret",
                "google_calendar_refresh_token": "calendar-refresh-token",
            },
        ),
        user,
        async_session,
    )

    assert result.integration_config["providers"]["discovery"] == "tavily"
    assert result.credential_configured["gemini_api_key"] is True
    assert result.credential_configured["tavily_api_key"] is True
    assert result.integrations[0].status == "configured"
    assert any(item.id == "calendar" for item in result.integrations)
    assert "organization-gemini-secret" not in json.dumps(result.model_dump())

    organization = await async_session.get(Organization, user.organization_id)
    assert organization is not None
    stored_settings = json.dumps(organization.settings)
    assert "organization-gemini-secret" not in stored_settings
    assert "calendar-refresh-token" not in stored_settings
    assert "integration_secrets" in organization.settings

    effective = get_organization_runtime_settings(organization, config)
    assert effective.GEMINI_API_KEY == "organization-gemini-secret"
    assert effective.TAVILY_API_KEY == "organization-tavily-secret"
    assert effective.LLM_PROVIDER == "gemini"
    assert effective.GEMINI_MODEL == "gemini-test-model"
    assert effective.GROQ_MODEL == "groq-model-unchanged"
    assert effective.CALENDAR_PROVIDER == "google"


@pytest.mark.asyncio
async def test_integration_credentials_require_encryption_key(
    async_session,
    monkeypatch,
):
    config = Settings(INTEGRATION_ENCRYPTION_KEY="")
    monkeypatch.setattr(settings_api, "get_settings", lambda: config)
    monkeypatch.setattr(integration_settings_service, "get_settings", lambda: config)
    user = await create_settings_user(async_session)

    with pytest.raises(HTTPException) as error:
        await settings_api.save_integration_settings(
            settings_api.IntegrationSettingsUpdatePayload(
                secrets={"gemini_api_key": "should-not-be-stored"}
            ),
            user,
            async_session,
        )

    assert error.value.status_code == 503


@pytest.mark.asyncio
async def test_only_organization_admins_can_change_integrations(
    async_session,
    monkeypatch,
):
    monkeypatch.setattr(settings_api, "get_settings", lambda: Settings())
    member = await create_settings_user(async_session)
    member.role = "member"

    with pytest.raises(HTTPException) as error:
        await settings_api.save_integration_settings(
            settings_api.IntegrationSettingsUpdatePayload(
                providers={"llm": "groq"}
            ),
            member,
            async_session,
        )

    assert error.value.status_code == 403
