import secrets
from uuid import UUID

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import APIKey

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hash(raw_key)


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.verify(raw_key, hashed)


def generate_api_key() -> str:
    return f"idp_{secrets.token_urlsafe(32)}"


async def get_current_client(
    request: Request,
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> APIKey:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    # Look up all active keys and verify
    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)  # noqa: E712
    )
    keys = result.scalars().all()

    for key_record in keys:
        if verify_api_key(api_key, key_record.key_hash):
            request.state.client_id = key_record.client_id
            return key_record

    raise HTTPException(status_code=403, detail="Invalid API key")


async def get_optional_client(
    request: Request,
    api_key: str | None = Security(api_key_header),
    db: AsyncSession = Depends(get_db),
) -> APIKey | None:
    """Same as get_current_client but returns None instead of raising if no key."""
    if not api_key:
        request.state.client_id = None
        return None

    result = await db.execute(
        select(APIKey).where(APIKey.is_active == True)  # noqa: E712
    )
    keys = result.scalars().all()

    for key_record in keys:
        if verify_api_key(api_key, key_record.key_hash):
            request.state.client_id = key_record.client_id
            return key_record

    raise HTTPException(status_code=403, detail="Invalid API key")
