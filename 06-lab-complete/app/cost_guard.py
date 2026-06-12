"""
Cost Guard — monthly budget per user in Redis.

Mỗi user: $10/tháng (MONTHLY_BUDGET_USD). State trong Redis để scale ngang.
"""
import logging
from datetime import datetime

from fastapi import HTTPException

from app.config import settings

logger = logging.getLogger(__name__)

PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006
BUDGET_KEY_TTL_SECONDS = 32 * 24 * 3600

_redis_client = None
_redis_checked = False
_fallback_store: dict[str, float] = {}


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
        logger.warning("Redis unavailable for cost guard, using in-memory fallback: %s", exc)
        return None


def _month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def _budget_key(user_id: str) -> str:
    return f"budget:{user_id}:{_month_key()}"


def estimate_token_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return round(input_cost + output_cost, 6)


def _get_current_spend(user_id: str) -> float:
    key = _budget_key(user_id)
    client = _get_redis()
    if client:
        return float(client.get(key) or 0)
    return _fallback_store.get(key, 0.0)


def check_budget(user_id: str, estimated_cost: float) -> None:
    """Raise HTTP 402 if monthly budget would be exceeded."""
    if estimated_cost < 0:
        estimated_cost = 0.0

    current = _get_current_spend(user_id)
    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(current, 4),
                "budget_usd": settings.monthly_budget_usd,
                "resets_at": "start of next month",
            },
        )


def record_usage(user_id: str, input_tokens: int, output_tokens: int) -> float:
    """Record actual cost after LLM call. Returns cost in USD."""
    cost = estimate_token_cost(input_tokens, output_tokens)
    key = _budget_key(user_id)
    current = _get_current_spend(user_id)

    if current + cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded after request",
                "used_usd": round(current, 4),
                "budget_usd": settings.monthly_budget_usd,
            },
        )

    client = _get_redis()
    if client:
        client.incrbyfloat(key, cost)
        client.expire(key, BUDGET_KEY_TTL_SECONDS)
    else:
        _fallback_store[key] = current + cost

    return cost


def get_budget_remaining(user_id: str) -> float:
    return max(0.0, settings.monthly_budget_usd - _get_current_spend(user_id))
