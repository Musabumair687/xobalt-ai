import logging

import redis
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()
redis_client = redis.Redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=1,
    socket_timeout=1,
)

def check_redis_connection() -> bool:
    try:
        return redis_client.ping()
    except Exception as exc:
        logger.warning("Redis readiness check failed (%s).", type(exc).__name__)
        return False