"""API Key authentication."""
from fastapi import Header, HTTPException

from app.config import settings


def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """
    Verify X-API-Key header against AGENT_API_KEY env var.
    Returns the validated key on success.
    """
    if not x_api_key or x_api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return x_api_key
