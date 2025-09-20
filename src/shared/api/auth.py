# src/shared/api/auth.py

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from fastapi import Request, HTTPException, status

class ModuleAPIKey(BaseModel):
    module_name: str
    api_key: str
    permissions: List[str]
    expires_at: Optional[datetime] = None

# A simple in-memory store for API keys. In a real application, this would
# be stored securely in a database or a secret management system.
API_KEYS = {
    "narrative_module_key": ModuleAPIKey(
        module_name="narrative",
        api_key="narrative_module_key",
        permissions=["read:narrative", "write:narrative"],
    ),
    "gamification_module_key": ModuleAPIKey(
        module_name="gamification",
        api_key="gamification_module_key",
        permissions=["read:gamification", "write:gamification"],
    ),
    "admin_module_key": ModuleAPIKey(
        module_name="admin",
        api_key="admin_module_key",
        permissions=["read:admin", "write:admin"],
    ),
}

async def authenticate_module_request(request: Request) -> str:
    """
    Validates an API key from the request headers and returns the module name if valid.
    """
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key missing",
        )

    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    key_data = API_KEYS[api_key]
    if key_data.expires_at and key_data.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API Key has expired",
        )

    return key_data.module_name
