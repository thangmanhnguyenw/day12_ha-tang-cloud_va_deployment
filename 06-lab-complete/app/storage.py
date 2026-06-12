"""Redis-backed session storage — stateless design for horizontal scaling."""
import json
import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False
_memory_store: dict[str, dict] = {}


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
        logger.warning("Redis unavailable for sessions, using in-memory fallback: %s", exc)
        return None


def redis_ping() -> bool:
    client = _get_redis()
    if not client:
        return False
    try:
        client.ping()
        return True
    except Exception:
        return False


def uses_redis() -> bool:
    return _get_redis() is not None


def save_session(session_id: str, data: dict) -> None:
    serialized = json.dumps(data)
    client = _get_redis()
    if client:
        client.setex(f"session:{session_id}", settings.session_ttl_seconds, serialized)
    else:
        _memory_store[f"session:{session_id}"] = data


def load_session(session_id: str) -> dict:
    client = _get_redis()
    if client:
        raw = client.get(f"session:{session_id}")
        return json.loads(raw) if raw else {}
    return _memory_store.get(f"session:{session_id}", {})


def append_to_history(session_id: str, role: str, content: str) -> list:
    session = load_session(session_id)
    history = session.get("history", [])
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    if len(history) > 20:
        history = history[-20:]
    session["history"] = history
    save_session(session_id, session)
    return history
