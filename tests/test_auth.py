import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    hash_api_key,
    hash_password,
    verify_password,
)
from tests.conftest import (
    TEST_ADMIN_RAW_KEY,
    TEST_CLIENT_ID,
    TEST_RAW_API_KEY,
    TEST_USER_EMAIL,
    TEST_USER_PASSWORD,
)


# ---------------------------------------------------------------------------
# Hash & generate helpers
# ---------------------------------------------------------------------------
class TestAPIKeyHelpers:
    def test_hash_api_key_deterministic(self):
        key = "dp_live_abcdef1234567890abcdef1234567890"
        assert hash_api_key(key) == hash_api_key(key)

    def test_hash_api_key_length(self):
        h = hash_api_key("anything")
        assert len(h) == 64  # SHA-256 hex

    def test_generate_api_key_format(self):
        raw_key, prefix = generate_api_key()
        assert raw_key.startswith("dp_live_")
        assert len(raw_key) == 40  # "dp_live_" (8) + 32 hex chars
        assert prefix == raw_key[:12]

    def test_generate_api_key_unique(self):
        keys = {generate_api_key()[0] for _ in range(20)}
        assert len(keys) == 20


class TestPasswordHelpers:
    def test_hash_and_verify(self):
        h = hash_password("secret123")
        assert verify_password("secret123", h)

    def test_wrong_password(self):
        h = hash_password("secret123")
        assert not verify_password("wrong", h)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
class TestJWTHelpers:
    def test_create_and_decode_access_token(self):
        uid = str(uuid.uuid4())
        token = create_access_token(uid, "client-x", "admin")
        payload = decode_token(token)
        assert payload["sub"] == uid
        assert payload["client_id"] == "client-x"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_create_and_decode_refresh_token(self):
        uid = str(uuid.uuid4())
        token = create_refresh_token(uid, "client-y", "member")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_expired_token(self):
        from jose import JWTError

        uid = str(uuid.uuid4())
        # Patch expiry to -1 minute
        with patch("app.auth.settings") as mock_settings:
            mock_settings.JWT_SECRET_KEY = "test-secret"
            mock_settings.JWT_ALGORITHM = "HS256"
            mock_settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES = -1
            token = create_access_token(uid, "c", "member")

        with pytest.raises(JWTError):
            decode_token(token)


# ---------------------------------------------------------------------------
# Auth flow integration (via HTTP)
# ---------------------------------------------------------------------------
class TestAPIKeyAuth:
    @pytest.mark.asyncio
    async def test_valid_api_key(self, client, auth_headers):
        resp = await client.get("/api/v1/documents/", headers=auth_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, client):
        resp = await client.get(
            "/api/v1/documents/",
            headers={"X-API-Key": "dp_live_invalid_key_doesnt_exist99"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_no_credentials(self, client):
        resp = await client.get("/api/v1/documents/")
        assert resp.status_code == 401


class TestJWTAuth:
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert data["client_id"] == TEST_CLIENT_ID

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_bearer_auth(self, client):
        # Login first
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        token = login_resp.json()["access_token"]

        # Use token
        resp = await client.get(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_token(self, client):
        # Login
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        refresh_token = login_resp.json()["refresh_token"]

        # Refresh
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, client):
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": TEST_USER_EMAIL, "password": TEST_USER_PASSWORD},
        )
        access_token = login_resp.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


class TestRBAC:
    @pytest.mark.asyncio
    async def test_admin_key_can_access_admin_routes(self, client, admin_headers):
        resp = await client.get("/api/v1/admin/api-keys", headers=admin_headers)
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_member_key_cannot_access_admin_routes(self, client, auth_headers):
        resp = await client.get("/api/v1/admin/api-keys", headers=auth_headers)
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth_cannot_access_admin_routes(self, client):
        resp = await client.get("/api/v1/admin/api-keys")
        assert resp.status_code == 401


class TestSignup:
    @pytest.mark.asyncio
    async def test_signup_success(self, client):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Acme Corp",
                "email": "newuser@acme.com",
                "password": "securepass123",
                "name": "John Doe",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_id"] == "acme-corp"
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == "newuser@acme.com"
        assert data["user"]["role"] == "admin"
        assert data["user"]["client_id"] == "acme-corp"

    @pytest.mark.asyncio
    async def test_signup_then_login(self, client):
        # Signup
        await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Login Test Co",
                "email": "login@test.com",
                "password": "mypassword99",
            },
        )
        # Login with same credentials
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "login@test.com", "password": "mypassword99"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_signup_token_works_for_upload(self, client):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Upload Test",
                "email": "upload@test.com",
                "password": "securepass1",
            },
        )
        token = resp.json()["access_token"]

        # Use token to list documents
        docs_resp = await client.get(
            "/api/v1/documents/",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert docs_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_signup_duplicate_email(self, client):
        await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "First Co",
                "email": "dup@test.com",
                "password": "password123",
            },
        )
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Second Co",
                "email": "dup@test.com",
                "password": "password456",
            },
        )
        assert resp.status_code == 409
        assert "Email already registered" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_signup_duplicate_client_name(self, client):
        await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Same Name",
                "email": "first@test.com",
                "password": "password123",
            },
        )
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Same Name",
                "email": "second@test.com",
                "password": "password456",
            },
        )
        assert resp.status_code == 409
        assert "Client name already taken" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_signup_short_password(self, client):
        resp = await client.post(
            "/api/v1/auth/signup",
            json={
                "client_name": "Short PW",
                "email": "short@test.com",
                "password": "abc",
            },
        )
        assert resp.status_code == 422
