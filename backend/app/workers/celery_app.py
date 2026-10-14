"""Celery application shared by API producers and worker processes."""

import logging

from celery import Celery
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "xobalt_ai",
    broker=settings.REDIS_URL,
    include=["app.workers.campaign_tasks"],
)
celery_app.conf.update(
    accept_content=["json"],
    task_serializer="json",
    result_serializer="json",
    task_ignore_result=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    broker_connection_timeout=2,
    broker_connection_max_retries=0,
    broker_transport_options={
        "visibility_timeout": 21600,
        "socket_connect_timeout": 1,
        "socket_timeout": 1,
    },
)


def check_worker_connection() -> bool:
    """Return whether a Celery worker responds to a broker control ping."""
    try:
        response = celery_app.control.inspect(timeout=1.0).ping()
        return bool(response)
    except Exception as exc:
        logger.warning("Celery worker readiness check failed (%s).", type(exc).__name__)
        return False
