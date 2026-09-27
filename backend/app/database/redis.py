import redis
from backend.app.config.settings import settings

redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)

def check_redis_connection() -> bool:
    try:
        return redis_client.ping()
    except Exception:
        return False