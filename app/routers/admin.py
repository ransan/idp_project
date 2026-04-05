from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_api_key, hash_api_key, hash_password, require_admin
from app.database import get_db
from app.models import APIKey, Client, User
from app.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyResponse,
    ClientCreateRequest,
    ClientResponse,
    UserCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ---------------------------------------------------------------------------
# Client CRUD
# ---------------------------------------------------------------------------
@router.post("/clients", response_model=ClientResponse, status_code=201)
async def create_client(
    payload: ClientCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    # Check duplicate
    existing = await db.execute(select(Client).where(Client.id == payload.id))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Client ID already exists")

    client = Client(
        id=payload.id,
        name=payload.name,
        email=payload.email,
        plan=payload.plan,
        rate_limit=payload.rate_limit,
    )
    db.add(client)
    await db.flush()

    return ClientResponse(
        id=client.id,
        name=client.name,
        email=client.email,
        plan=client.plan,
        rate_limit=client.rate_limit,
        is_active=client.is_active,
        created_at=client.created_at,
    )


@router.get("/clients", response_model=list[ClientResponse])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    result = await db.execute(select(Client).order_by(Client.created_at.desc()))
    clients = result.scalars().all()
    return [
        ClientResponse(
            id=c.id,
            name=c.name,
            email=c.email,
            plan=c.plan,
            rate_limit=c.rate_limit,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in clients
    ]


# ---------------------------------------------------------------------------
# API Key CRUD
# ---------------------------------------------------------------------------
@router.post("/api-keys", response_model=APIKeyCreateResponse, status_code=201)
async def create_api_key(
    payload: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    # Verify client exists
    client_result = await db.execute(select(Client).where(Client.id == payload.client_id))
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    raw_key, key_prefix = generate_api_key()
    key_record = APIKey(
        key_hash=hash_api_key(raw_key),
        key_prefix=key_prefix,
        client_id=payload.client_id,
        name=payload.name,
        role=payload.role,
        rate_limit=payload.rate_limit,
    )
    db.add(key_record)
    await db.flush()

    return APIKeyCreateResponse(
        id=key_record.id,
        client_id=key_record.client_id,
        name=key_record.name,
        raw_key=raw_key,
        key_prefix=key_prefix,
        role=key_record.role,
        rate_limit=key_record.rate_limit,
    )


@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    result = await db.execute(select(APIKey).order_by(APIKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        APIKeyResponse(
            id=k.id,
            client_id=k.client_id,
            name=k.name,
            key_prefix=k.key_prefix,
            role=k.role,
            is_active=k.is_active,
            rate_limit=k.rate_limit,
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@router.delete("/api-keys/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    result = await db.execute(select(APIKey).where(APIKey.id == UUID(key_id)))
    key_record = result.scalar_one_or_none()
    if not key_record:
        raise HTTPException(status_code=404, detail="API key not found")
    key_record.is_active = False
    await db.flush()


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------
@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    payload: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin: dict = Depends(require_admin),
):
    # Verify client exists
    client_result = await db.execute(select(Client).where(Client.id == payload.client_id))
    if not client_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Client not found")

    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        client_id=payload.client_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role=payload.role,
    )
    db.add(user)
    await db.flush()

    return UserResponse(
        id=user.id,
        client_id=user.client_id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
    )
