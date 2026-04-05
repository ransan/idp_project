import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models import APIKey, User

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# API Key helpers
# ---------------------------------------------------------------------------
def hash_api_key(raw_key: str) -> str:
    """One-way SHA-256 hash — the plaintext key is never stored."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str]:
    """Generate a new API key. Returns (raw_key, key_prefix)."""
    random_hex = secrets.token_hex(16)  # 32 hex chars
    raw_key = f"dp_live_{random_hex}"
    key_prefix = raw_key[:12]  # "dp_live_a1b2"
    return raw_key, key_prefix


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return bcrypt.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.verify(password, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
def create_access_token(
    user_id: str, client_id: str, role: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "client_id": client_id,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    user_id: str, client_id: str, role: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "client_id": client_id,
        "role": role,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises JWTError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Auth dependencies
# ---------------------------------------------------------------------------
async def get_current_client(
    request: Request,
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resolves the authenticated client from EITHER:
      - X-API-Key header (programmatic access)
      - Bearer JWT token (dashboard access)

    Returns: {"client_id": "...", "role": "member|admin", "method": "api_key|jwt"}
    """

    # --- Path 1: API Key ---
    if api_key:
        key_hash = hash_api_key(api_key)
        result = await db.execute(
            select(APIKey).where(
                APIKey.key_hash == key_hash,
                APIKey.is_active == True,  # noqa: E712
            )
        )
        key_record = result.scalar_one_or_none()

        if not key_record:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Check expiration
        if key_record.expires_at and key_record.expires_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=401, detail="API key expired")

        # Update last_used timestamp
        key_record.last_used_at = datetime.now(timezone.utc)
        await db.commit()

        auth_info = {
            "client_id": key_record.client_id,
            "role": key_record.role,
            "method": "api_key",
        }
        request.state.client_id = key_record.client_id
        request.state.auth = auth_info
        return auth_info

    # --- Path 2: JWT Bearer Token ---
    if bearer:
        try:
            payload = decode_token(bearer.credentials)
            if payload.get("type") != "access":
                raise HTTPException(status_code=401, detail="Invalid token type")

            auth_info = {
                "client_id": payload["client_id"],
                "role": payload.get("role", "member"),
                "method": "jwt",
            }
            request.state.client_id = payload["client_id"]
            request.state.auth = auth_info
            return auth_info
        except JWTError:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

    # --- No credentials provided ---
    raise HTTPException(
        status_code=401,
        detail="Authentication required. Provide X-API-Key header or Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_client(
    request: Request,
    api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict | None:
    """Same as get_current_client but returns None instead of raising if no credentials."""
    if not api_key and not bearer:
        request.state.client_id = None
        request.state.auth = None
        return None

    return await get_current_client(request, api_key, bearer, db)


def require_admin(client: dict = Depends(get_current_client)) -> dict:
    """Dependency that enforces admin role."""
    if client["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return client
