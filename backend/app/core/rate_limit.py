import time
import redis
from fastapi import HTTPException
from app.core.redis_client import redis_client

# Max analysis requests per user per window
RATE_LIMIT_MAX_REQUESTS = 10
RATE_LIMIT_WINDOW_SECONDS = 3600  # 1 hour


def check_rate_limit(user_id: int, action: str = "analysis") -> None:
    """
    Fixed-window rate limiter backed by Redis.

    Raises HTTP 429 if the user has exceeded the limit.
    Fails open (allows the request) if Redis is unavailable — a rate
    limiter outage should not take down the whole API.
    """
    # Bucket requests into fixed windows: all requests in the same
    # hour share one counter key.
    window = int(time.time()) // RATE_LIMIT_WINDOW_SECONDS
    key = f"ratelimit:{action}:{user_id}:{window}"

    try:
        # INCR is atomic: increments and returns the new value in one operation.
        # No read-then-write race condition even under concurrent requests.
        current = redis_client.incr(key)

        # On the first request in this window, set the key to expire.
        # Redis cleans it up automatically — no cleanup job needed.
        if current == 1:
            redis_client.expire(key, RATE_LIMIT_WINDOW_SECONDS)

        if current > RATE_LIMIT_MAX_REQUESTS:
            ttl = redis_client.ttl(key)
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. Max {RATE_LIMIT_MAX_REQUESTS} "
                    f"analyses per hour. Try again in {ttl} seconds."
                ),
            )

    except redis.RedisError:
        # Redis is down — fail open rather than blocking all users.
        return