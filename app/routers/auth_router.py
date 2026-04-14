import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import Client, User
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    SignupRequest,
    SignupResponse,
    TokenResponse,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _slugify(name: str) -> str:
    """Convert a client name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")[:128]


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(
    payload: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Public signup: creates a new client + admin user, returns JWT tokens."""
    # Check duplicate email
    existing_user = await db.execute(
        select(User).where(User.email == payload.email)
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Generate client ID from name
    client_id = _slugify(payload.client_name)
    if not client_id:
        raise HTTPException(status_code=400, detail="Invalid client name")

    # Check duplicate client
    existing_client = await db.execute(
        select(Client).where(Client.id == client_id)
    )
    if existing_client.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Client name already taken")

    # Create client
    client = Client(
        id=client_id,
        name=payload.client_name,
        email=payload.email,
    )
    db.add(client)
    await db.flush()

    # Create admin user
    user = User(
        client_id=client_id,
        email=payload.email,
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="admin",
    )
    db.add(user)
    await db.flush()

    # Generate tokens
    user_id = str(user.id)
    access_token = create_access_token(user_id, client_id, user.role)
    refresh_token = create_refresh_token(user_id, client_id, user.role)

    return SignupResponse(
        user=UserResponse(
            id=user.id,
            client_id=user.client_id,
            email=user.email,
            name=user.name,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        client_id=client_id,
    )

@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email + password, receive JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == payload.email)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account is deactivated")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    user_id = str(user.id)
    access_token = create_access_token(user_id, user.client_id, user.role)
    refresh_token = create_refresh_token(user_id, user.client_id, user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        client_id=user.client_id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a new access token pair."""
    try:
        token_data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if token_data.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    # Verify user still active
    from uuid import UUID
    result = await db.execute(
        select(User).where(User.id == UUID(token_data["sub"]))
    )
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")

    user_id = str(user.id)
    access_token = create_access_token(user_id, user.client_id, user.role)
    refresh_token_new = create_refresh_token(user_id, user.client_id, user.role)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_new,
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        client_id=user.client_id,
    )
