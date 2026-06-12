"""
Redis-backed sliding window rate limiter.

10 requests/minute per user (configurable via RATE_LIMIT_PER_MINUTE).
Falls back to in-memory deque when Redis is unavailable (local dev only).
"""
import logging
import time
import uuid
from collections import defaultdict, deque

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False
_fallback_windows: dict[str, deque] = defaultdict(deque)


def _get_redis():
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not settings.redis_url:
        return None
    try:
        import redis

        client = redis.from_url(
            settings.redis_url, decode_responses=True, socket_connect_timeout=2
        )
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable for rate limiting, using in-memory fallback: %s", exc)
        return None


def _raise_rate_limited(limit: int, window_seconds: int, retry_after: int) -> None:
    raise HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "limit": limit,
            "window_seconds": window_seconds,
            "retry_after_seconds": retry_after,
        },
        headers={
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": "0",
            "Retry-After": str(retry_after),
        },
    )


def check_rate_limit(user_id: str) -> dict:
    """Sliding window: raise 429 if user exceeds limit."""
    limit = settings.rate_limit_per_minute
    window_seconds = 60
    now = time.time()
    key = f"ratelimit:{user_id}"

    client = _get_redis()
    if client:
        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, now - window_seconds)
        pipe.zcard(key)
        results = pipe.execute()
        count = results[1]

        if count >= limit:
            oldest = client.zrange(key, 0, 0, withscores=True)
            retry_after = window_seconds
            if oldest:
                retry_after = max(1, int(oldest[0][1] + window_seconds - now))
            _raise_rate_limited(limit, window_seconds, retry_after)

        client.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
        client.expire(key, window_seconds + 1)
        return {"limit": limit, "remaining": limit - count - 1}

    # In-memory fallback (not scalable)
    window = _fallback_windows[user_id]
    while window and window[0] < now - window_seconds:
        window.popleft()

    if len(window) >= limit:
        retry_after = max(1, int(window[0] + window_seconds - now))
        _raise_rate_limited(limit, window_seconds, retry_after)

    window.append(now)
    return {"limit": limit, "remaining": limit - len(window)}
