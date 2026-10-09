"""Tests for Approval Service."""

import pytest
import uuid
from unittest.mock import AsyncMock
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.database.base import Base
from app.models.message import Message
from app.services.approval_service import ApprovalService

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
async def test_approve_message(db_session: AsyncSession):
    # Setup
    org_id = uuid.uuid4()
    msg = Message(organization_id=org_id, channel="email", direction="outbound", subject="Test", body="Test", status="pending_approval")
    db_session.add(msg)
    await db_session.commit()
    
    service = ApprovalService(db_session)
    
    # Approve
    updated = await service.process_approval(msg.id, "approve")
    assert updated.status == "approved"
    
    # Edit and Approve
    updated = await service.process_approval(msg.id, "edit", edited_subject="New Subject")
    assert updated.status == "approved"
    assert updated.subject == "New Subject"
    
    # Reject
    updated = await service.process_approval(msg.id, "reject", reason="Bad tone")
    assert updated.status == "rejected"
    assert updated.metadata_["rejection_reason"] == "Bad tone"
    
    # Regenerate
    updated = await service.process_approval(msg.id, "regenerate")
    assert updated.status == "draft"
