import pytest
from fastapi import HTTPException
from app.core.rate_limit import check_rate_limit, RATE_LIMIT_MAX_REQUESTS
from app.core.redis_client import redis_client, is_redis_available


def _clear_user(user_id: int):
    for key in redis_client.scan_iter(f"ratelimit:*:{user_id}:*"):
        redis_client.delete(key)


@pytest.mark.skipif(not is_redis_available(), reason="Redis not available")
def test_allows_requests_under_limit():
    user_id = 90001
    _clear_user(user_id)
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        check_rate_limit(user_id)
    _clear_user(user_id)


@pytest.mark.skipif(not is_redis_available(), reason="Redis not available")
def test_blocks_requests_over_limit():
    user_id = 90002
    _clear_user(user_id)
    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        check_rate_limit(user_id)

    with pytest.raises(HTTPException) as exc:
        check_rate_limit(user_id)
    assert exc.value.status_code == 429
    _clear_user(user_id)


@pytest.mark.skipif(not is_redis_available(), reason="Redis not available")
def test_limits_are_per_user():
    user_a, user_b = 90003, 90004
    _clear_user(user_a)
    _clear_user(user_b)

    for _ in range(RATE_LIMIT_MAX_REQUESTS):
        check_rate_limit(user_a)
    with pytest.raises(HTTPException):
        check_rate_limit(user_a)

    check_rate_limit(user_b)

    _clear_user(user_a)
    _clear_user(user_b)