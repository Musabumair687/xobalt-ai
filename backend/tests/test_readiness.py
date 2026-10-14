import pytest
from fastapi import HTTPException

from app import main


@pytest.mark.asyncio
async def test_readiness_reports_database_broker_and_worker(monkeypatch):
    async def database_ok():
        return True

    monkeypatch.setattr(main, "database_ready", database_ok)
    monkeypatch.setattr(main, "check_redis_connection", lambda: True)
    monkeypatch.setattr(main, "check_worker_connection", lambda: True)

    result = await main.readiness_check()

    assert result == {
        "status": "ready",
        "checks": {
            "database": "available",
            "queue_broker": "available",
            "worker": "available",
        },
    }


@pytest.mark.asyncio
async def test_readiness_returns_service_unavailable_when_worker_is_down(monkeypatch):
    async def database_ok():
        return True

    monkeypatch.setattr(main, "database_ready", database_ok)
    monkeypatch.setattr(main, "check_redis_connection", lambda: True)
    monkeypatch.setattr(main, "check_worker_connection", lambda: False)

    with pytest.raises(HTTPException) as error:
        await main.readiness_check()

    assert error.value.status_code == 503
    assert error.value.detail["checks"]["worker"] == "unavailable"
