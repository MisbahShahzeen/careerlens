import redis
from app.core.config import settings

# decode_responses=True makes Redis return Python strings instead of bytes
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)


def is_redis_available() -> bool:
    """Check if Redis is reachable. Used to fail open if Redis is down."""
    try:
        redis_client.ping()
        return True
    except redis.RedisError:
        return False