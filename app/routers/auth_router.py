from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import LoginRequest, RefreshRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
