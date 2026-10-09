"""Tests for Outreach Service."""

import pytest
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.message import Message
from app.services.outreach_service import OutreachService
from app.integrations.email.base import EmailProvider

class MockEmailProvider(EmailProvider):
    async def send_email(self, to_email: str, subject: str, body: str, from_email=None) -> str:
        if "fail" in to_email:
            raise Exception("Provider temporary failure")
        return "mock-external-id"

@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest.mark.asyncio
async def test_outreach_send_success(db_session: AsyncSession):
    org_id = uuid.uuid4()
    msg = Message(organization_id=org_id, channel="email", direction="outbound", status="approved", body="Hello", subject="Subject")
    db_session.add(msg)
    await db_session.commit()
    
    provider = MockEmailProvider()
    service = OutreachService(db_session, provider)
    
    ext_id = await service.send_message(msg, "test@test.com")
    assert ext_id == "mock-external-id"
    assert msg.status == "sent"
    assert msg.external_id == "mock-external-id"
    assert msg.sent_at is not None

@pytest.mark.asyncio
async def test_outreach_send_failure(db_session: AsyncSession):
    org_id = uuid.uuid4()
    msg = Message(organization_id=org_id, channel="email", direction="outbound", status="approved", body="Hello", subject="Subject")
    db_session.add(msg)
    await db_session.commit()
    
    provider = MockEmailProvider()
    service = OutreachService(db_session, provider)
    
    with pytest.raises(Exception):
        await service.send_message(msg, "fail@test.com")
        
    assert msg.status == "failed"
    assert msg.metadata_["send_error"] == "Provider temporary failure"
