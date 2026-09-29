import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_database_connection(async_session: AsyncSession):
    result = await async_session.execute(text("SELECT 1"))
    assert result.scalar() == 1

@pytest.mark.asyncio
async def test_session_creation(async_session: AsyncSession):
    assert async_session is not None
    assert async_session.is_active

@pytest.mark.asyncio
async def test_tables_created(async_session: AsyncSession):
    result = await async_session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result.all()]
    
    assert "organizations" in tables
    assert "companies" in tables
    assert "leads" in tables
