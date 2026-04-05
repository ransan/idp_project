from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_api_key, get_current_client, hash_api_key
from app.database import get_db
from app.models import APIKey
from app.schemas import APIKeyCreateRequest, APIKeyCreateResponse, APIKeyResponse

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    raw_key = generate_api_key()
    key_record = APIKey(
        key_hash=hash_api_key(raw_key),
        client_id=payload.client_id,
        name=payload.name,
        rate_limit=payload.rate_limit,
    )
    db.add(key_record)
    await db.flush()

    return APIKeyCreateResponse(
        id=key_record.id,
        client_id=key_record.client_id,
        name=key_record.name,
        raw_key=raw_key,
        rate_limit=key_record.rate_limit,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        APIKeyResponse(
            id=k.id,
            client_id=k.client_id,
            name=k.name,
            is_active=k.is_active,
            rate_limit=k.rate_limit,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
):
    from uuid import UUID

    result = await db.execute(select(APIKey).where(APIKey.id == UUID(key_id)))
    key_record = result.scalar_one_or_none()
    if not key_record:
        raise HTTPException(status_code=404, detail="API key not found")
    key_record.is_active = False
    await db.flush()
