"""
Production AI Agent — kết hợp tất cả Day 12 concepts.

✅ Config từ environment (12-factor)
✅ Structured JSON logging
✅ API Key authentication
✅ Rate limiting (Redis sliding window)
✅ Cost guard ($10/month per user, Redis)
✅ Conversation history (Redis, stateless)
✅ Health + readiness probes
✅ Graceful shutdown (SIGTERM)
"""
import json
import logging
import os
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_token_cost, get_budget_remaining, record_usage
from app.rate_limiter import check_rate_limit
from app.storage import append_to_history, load_session, redis_ping, uses_redis
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
INSTANCE_ID = os.getenv("INSTANCE_ID", f"instance-{uuid.uuid4().hex[:6]}")
_is_ready = False
_in_flight_requests = 0
_request_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": INSTANCE_ID,
        "storage": "redis" if uses_redis() else "in-memory",
    }))
    time.sleep(0.1)
    _is_ready = True
    logger.info(json.dumps({"event": "ready", "instance": INSTANCE_ID}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown_started", "in_flight": _in_flight_requests}))
    deadline = time.time() + 30
    while _in_flight_requests > 0 and time.time() < deadline:
        time.sleep(0.1)
    logger.info(json.dumps({"event": "shutdown_complete"}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _in_flight_requests

    if request.url.path not in ("/health", "/ready") and not _is_ready:
        return JSONResponse(status_code=503, content={"detail": "Service shutting down"})

    _in_flight_requests += 1
    _request_count += 1
    start = time.time()
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Served-By"] = INSTANCE_ID
        if "server" in response.headers:
            del response.headers["server"]
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.time() - start) * 1000, 1),
            "instance": INSTANCE_ID,
        }))
        return response
    finally:
        _in_flight_requests -= 1


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(default="default", min_length=1, max_length=64)
    session_id: str | None = Field(default=None, max_length=64)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    session_id: str
    turn: int
    served_by: str
    storage: str
    usage: dict
    timestamp: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": INSTANCE_ID,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    _api_key: str = Depends(verify_api_key),
):
    """Send a question to the AI agent. Conversation history stored in Redis."""
    rate_info = check_rate_limit(body.user_id)

    input_tokens = len(body.question.split()) * 2
    estimated = estimate_token_cost(input_tokens, 0)
    check_budget(body.user_id, estimated)

    session_id = body.session_id or body.user_id
    append_to_history(session_id, "user", body.question)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "session_id": session_id,
        "q_len": len(body.question),
        "instance": INSTANCE_ID,
    }))

    answer = llm_ask(body.question)
    output_tokens = len(answer.split()) * 2
    cost = record_usage(body.user_id, input_tokens, output_tokens)

    history = append_to_history(session_id, "assistant", answer)
    turn = len([m for m in history if m["role"] == "user"])

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        session_id=session_id,
        turn=turn,
        served_by=INSTANCE_ID,
        storage="redis" if uses_redis() else "in-memory",
        usage={
            "requests_remaining": rate_info["remaining"],
            "budget_remaining_usd": get_budget_remaining(body.user_id),
            "request_cost_usd": cost,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/history/{session_id}", tags=["Agent"])
def get_history(session_id: str, _api_key: str = Depends(verify_api_key)):
    session = load_session(session_id)
    if not session:
        raise HTTPException(404, f"Session {session_id} not found or expired")
    return {
        "session_id": session_id,
        "messages": session.get("history", []),
        "count": len(session.get("history", [])),
        "storage": "redis" if uses_redis() else "in-memory",
    }


@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe — process is alive."""
    redis_ok = redis_ping() if settings.redis_url else None
    status = "ok"
    if settings.redis_url and redis_ok is False:
        status = "degraded"
    return {
        "status": status,
        "version": settings.app_version,
        "instance": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "storage": "redis" if uses_redis() else "in-memory",
        "redis_connected": redis_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe — ready to accept traffic."""
    if not _is_ready:
        raise HTTPException(503, "Not ready — starting up or shutting down")
    if settings.redis_url and not redis_ping():
        raise HTTPException(503, "Redis not available")
    return {"ready": True, "instance": INSTANCE_ID, "in_flight_requests": _in_flight_requests}


def _handle_signal(signum, _frame):
    global _is_ready
    _is_ready = False
    logger.info(json.dumps({"event": "signal", "signum": signum, "instance": INSTANCE_ID}))


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


if __name__ == "__main__":
    logger.info(json.dumps({
        "event": "boot",
        "app": settings.app_name,
        "host": settings.host,
        "port": settings.port,
    }))
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
