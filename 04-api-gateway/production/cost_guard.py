"""
Cost Guard — Bảo Vệ Budget LLM

Mục tiêu: Tránh bill bất ngờ từ LLM API.
- Đếm chi phí đã dùng mỗi tháng
- Cảnh báo khi gần hết budget
- Block khi vượt budget

Production: lưu spending trong Redis (stateless, multi-instance safe).
"""
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Giá token (tham khảo, thay đổi theo model)
PRICE_PER_1K_INPUT_TOKENS = 0.00015   # GPT-4o-mini: $0.15/1M input
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006   # GPT-4o-mini: $0.60/1M output

MONTHLY_BUDGET_USD = float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BUDGET_KEY_TTL_SECONDS = 32 * 24 * 3600  # > 1 tháng → key tự hết hạn, reset ngầm

_redis_client = None
_redis_checked = False
_fallback_store: dict[str, float] = {}


def _get_redis():
    """Lazy Redis client; trả None nếu Redis không khả dụng (dev local)."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    try:
        import redis

        client = redis.from_url(REDIS_URL, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        _redis_client = client
        return _redis_client
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory fallback: %s", exc)
        return None


def _month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def _budget_key(user_id: str) -> str:
    return f"budget:{user_id}:{_month_key()}"


def _get_current_spend(user_id: str) -> float:
    key = _budget_key(user_id)
    client = _get_redis()
    if client:
        return float(client.get(key) or 0)
    return _fallback_store.get(key, 0.0)


def check_budget(user_id: str, estimated_cost: float) -> bool:
    """
    Return True nếu còn budget, False nếu vượt.

    Logic:
    - Mỗi user có budget $10/tháng
    - Track spending trong Redis
    - Reset đầu tháng (key theo YYYY-MM, TTL 32 ngày)
    """
    if estimated_cost < 0:
        estimated_cost = 0.0

    key = _budget_key(user_id)
    current = _get_current_spend(user_id)

    if current + estimated_cost > MONTHLY_BUDGET_USD:
        logger.warning(
            "Budget exceeded for %s: $%.4f + $%.4f > $%.2f",
            user_id,
            current,
            estimated_cost,
            MONTHLY_BUDGET_USD,
        )
        return False

    client = _get_redis()
    if client:
        client.incrbyfloat(key, estimated_cost)
        client.expire(key, BUDGET_KEY_TTL_SECONDS)
    else:
        _fallback_store[key] = current + estimated_cost

    return True


def has_budget(user_id: str, estimated_cost: float) -> bool:
    """Read-only pre-check trước khi gọi LLM (không ghi spending)."""
    if estimated_cost < 0:
        estimated_cost = 0.0
    return _get_current_spend(user_id) + estimated_cost <= MONTHLY_BUDGET_USD


def estimate_token_cost(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
    output_cost = (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    return round(input_cost + output_cost, 6)


@dataclass
class UsageRecord:
    user_id: str
    input_tokens: int = 0
    output_tokens: int = 0
    request_count: int = 0
    month: str = field(default_factory=_month_key)

    @property
    def total_cost_usd(self) -> float:
        return estimate_token_cost(self.input_tokens, self.output_tokens)


class CostGuard:
    def __init__(
        self,
        monthly_budget_usd: float = MONTHLY_BUDGET_USD,
        global_monthly_budget_usd: float = 100.0,
        warn_at_pct: float = 0.8,
    ):
        self.monthly_budget_usd = monthly_budget_usd
        self.global_monthly_budget_usd = global_monthly_budget_usd
        self.warn_at_pct = warn_at_pct
        self._records: dict[str, UsageRecord] = {}
        self._global_month = _month_key()
        self._global_cost = 0.0

    def _get_record(self, user_id: str) -> UsageRecord:
        month = _month_key()
        record = self._records.get(user_id)
        if not record or record.month != month:
            self._records[user_id] = UsageRecord(user_id=user_id, month=month)
        return self._records[user_id]

    def check_budget(self, user_id: str, estimated_cost: float = 0.001) -> None:
        """
        Kiểm tra budget trước khi gọi LLM.
        Raise 402 nếu vượt budget tháng.
        """
        if self._global_month != _month_key():
            self._global_month = _month_key()
            self._global_cost = 0.0

        if self._global_cost >= self.global_monthly_budget_usd:
            logger.critical("GLOBAL BUDGET EXCEEDED: $%.4f", self._global_cost)
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable due to budget limits.",
            )

        current_spend = _get_current_spend(user_id)
        if not has_budget(user_id, estimated_cost):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded",
                    "used_usd": round(current_spend, 4),
                    "budget_usd": self.monthly_budget_usd,
                    "resets_at": "start of next month",
                },
            )

        if current_spend >= self.monthly_budget_usd * self.warn_at_pct:
            logger.warning(
                "User %s at %.0f%% monthly budget",
                user_id,
                current_spend / self.monthly_budget_usd * 100,
            )

    def record_usage(
        self, user_id: str, input_tokens: int, output_tokens: int
    ) -> UsageRecord:
        """Ghi nhận usage sau khi gọi LLM xong và cập nhật Redis."""
        record = self._get_record(user_id)
        record.input_tokens += input_tokens
        record.output_tokens += output_tokens
        record.request_count += 1

        cost = estimate_token_cost(input_tokens, output_tokens)
        if not check_budget(user_id, cost):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "Monthly budget exceeded after request",
                    "used_usd": round(_get_current_spend(user_id), 4),
                    "budget_usd": self.monthly_budget_usd,
                },
            )

        self._global_cost += cost
        logger.info(
            "Usage: user=%s req=%s cost=$%.4f/$%.2f (month)",
            user_id,
            record.request_count,
            _get_current_spend(user_id),
            self.monthly_budget_usd,
        )
        return record

    def get_usage(self, user_id: str) -> dict:
        record = self._get_record(user_id)
        spent = _get_current_spend(user_id)
        return {
            "user_id": user_id,
            "month": record.month,
            "requests": record.request_count,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "cost_usd": spent,
            "budget_usd": self.monthly_budget_usd,
            "budget_remaining_usd": max(0, self.monthly_budget_usd - spent),
            "budget_used_pct": round(spent / self.monthly_budget_usd * 100, 1),
        }


cost_guard = CostGuard(monthly_budget_usd=MONTHLY_BUDGET_USD, global_monthly_budget_usd=100.0)
