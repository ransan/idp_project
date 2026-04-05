import io
import uuid
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import generate_api_key, hash_api_key
from app.models import APIKey, DocCategory, DocStatus, Document


# ---------------------------------------------------------------------------
# Helper: seed a document directly in DB
# ---------------------------------------------------------------------------
async def _seed_document(db_session, **kwargs):
    defaults = {
        "filename": f"{uuid.uuid4()}.pdf",
        "original_name": "test.pdf",
        "file_size": 1024,
        "mime_type": "application/pdf",
        "storage_path": f"/tmp/{uuid.uuid4()}.pdf",
        "status": DocStatus.UPLOADED,
        "client_id": "test_client",
    }
    defaults.update(kwargs)
    doc = Document(**defaults)
    db_session.add(doc)
    await db_session.commit()
    return doc


# ---------------------------------------------------------------------------
# Health & Stats
# ---------------------------------------------------------------------------
class TestHealthEndpoint:
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestStatsEndpoint:
    @pytest.mark.asyncio
    async def test_stats_empty(self, client):
        resp = await client.get("/api/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_documents"] == 0


# ---------------------------------------------------------------------------
# Upload Endpoints
# ---------------------------------------------------------------------------
class TestUploadEndpoint:
    @pytest.mark.asyncio
    async def test_upload_valid_pdf(self, client, sample_pdf_bytes, tmp_upload_dir):
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("invoice.pdf", sample_pdf_bytes, "application/pdf")},
            params={"client_id": "test"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "uploaded"
        assert data["original_name"] == "invoice.pdf"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_upload_valid_docx(self, client, sample_docx_bytes, tmp_upload_dir):
        resp = await client.post(
            "/api/v1/documents/upload",
            files={
                "file": (
                    "contract.docx",
                    sample_docx_bytes,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client, tmp_upload_dir):
        resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("script.py", b"print('hi')", "text/x-python")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_upload_file_too_large(self, client, tmp_upload_dir):
        from app.config import settings

        original = settings.MAX_FILE_SIZE_MB
        # Use object.__setattr__ to bypass Pydantic frozen/validation
        object.__setattr__(settings, "MAX_FILE_SIZE_MB", 0)
        try:
            resp = await client.post(
                "/api/v1/documents/upload",
                files={"file": ("test.pdf", b"x" * 100, "application/pdf")},
            )
            assert resp.status_code == 413
        finally:
            object.__setattr__(settings, "MAX_FILE_SIZE_MB", original)

    @pytest.mark.asyncio
    async def test_upload_no_file(self, client):
        resp = await client.post("/api/v1/documents/upload")
        assert resp.status_code == 422


class TestBatchUploadEndpoint:
    @pytest.mark.asyncio
    async def test_batch_upload(self, client, sample_pdf_bytes, tmp_upload_dir):
        files = [
            ("files", (f"doc{i}.pdf", sample_pdf_bytes, "application/pdf"))
            for i in range(3)
        ]
        resp = await client.post("/api/v1/documents/upload/batch", files=files)
        assert resp.status_code == 201
        data = resp.json()
        assert data["total"] == 3
        assert len(data["documents"]) == 3

    @pytest.mark.asyncio
    async def test_batch_upload_exceeds_max(self, client, sample_pdf_bytes, tmp_upload_dir):
        with patch("app.routers.documents.settings.MAX_BATCH_SIZE", 2):
            files = [
                ("files", (f"doc{i}.pdf", sample_pdf_bytes, "application/pdf"))
                for i in range(3)
            ]
            resp = await client.post("/api/v1/documents/upload/batch", files=files)
            assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_batch_upload_mixed_valid_invalid(self, client, sample_pdf_bytes, tmp_upload_dir):
        files = [
            ("files", ("valid.pdf", sample_pdf_bytes, "application/pdf")),
            ("files", ("bad.py", b"import os", "text/x-python")),
        ]
        resp = await client.post("/api/v1/documents/upload/batch", files=files)
        # Should reject because one file is invalid
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Get Document
# ---------------------------------------------------------------------------
class TestGetDocumentEndpoint:
    @pytest.mark.asyncio
    async def test_get_existing_document(self, client, sample_pdf_bytes, tmp_upload_dir):
        # First upload
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["status"] == "uploaded"

    @pytest.mark.asyncio
    async def test_get_nonexistent_document(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/v1/documents/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# List Documents
# ---------------------------------------------------------------------------
class TestListDocumentsEndpoint:
    @pytest.mark.asyncio
    async def test_list_empty(self, client):
        resp = await client.get("/api/v1/documents/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["documents"] == []

    @pytest.mark.asyncio
    async def test_list_with_documents(self, client, sample_pdf_bytes, tmp_upload_dir):
        # Upload 2 docs
        for i in range(2):
            await client.post(
                "/api/v1/documents/upload",
                files={"file": (f"doc{i}.pdf", sample_pdf_bytes, "application/pdf")},
            )

        resp = await client.get("/api/v1/documents/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["documents"]) == 2

    @pytest.mark.asyncio
    async def test_list_pagination(self, client, sample_pdf_bytes, tmp_upload_dir):
        for i in range(5):
            await client.post(
                "/api/v1/documents/upload",
                files={"file": (f"doc{i}.pdf", sample_pdf_bytes, "application/pdf")},
            )

        resp = await client.get("/api/v1/documents/", params={"page": 1, "size": 2})
        data = resp.json()
        assert data["total"] == 5
        assert len(data["documents"]) == 2
        assert data["page"] == 1
        assert data["size"] == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, client, sample_pdf_bytes, tmp_upload_dir):
        await client.post(
            "/api/v1/documents/upload",
            files={"file": ("doc.pdf", sample_pdf_bytes, "application/pdf")},
        )
        resp = await client.get("/api/v1/documents/", params={"status": "uploaded"})
        data = resp.json()
        assert data["total"] >= 1

        resp2 = await client.get("/api/v1/documents/", params={"status": "completed"})
        data2 = resp2.json()
        assert data2["total"] == 0


# ---------------------------------------------------------------------------
# Reprocess
# ---------------------------------------------------------------------------
class TestReprocessEndpoint:
    @pytest.mark.asyncio
    async def test_reprocess_existing(self, client, sample_pdf_bytes, tmp_upload_dir):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.post(f"/api/v1/documents/{doc_id}/reprocess")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "uploaded"
        assert "reprocessing" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_reprocess_nonexistent(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.post(f"/api/v1/documents/{fake_id}/reprocess")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
class TestDeleteEndpoint:
    @pytest.mark.asyncio
    async def test_delete_existing(self, client, sample_pdf_bytes, tmp_upload_dir):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.pdf", sample_pdf_bytes, "application/pdf")},
        )
        doc_id = upload_resp.json()["id"]

        resp = await client.delete(f"/api/v1/documents/{doc_id}")
        assert resp.status_code == 204

        # Verify it's gone
        get_resp = await client.get(f"/api/v1/documents/{doc_id}")
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/v1/documents/{fake_id}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Admin API Key Endpoints
# ---------------------------------------------------------------------------
class TestAdminAPIKeyEndpoints:
    @pytest.mark.asyncio
    async def test_create_api_key(self, client):
        resp = await client.post(
            "/api/v1/admin/api-keys",
            json={"client_id": "new_client", "name": "Test Key"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["client_id"] == "new_client"
        assert "raw_key" in data
        assert data["raw_key"].startswith("idp_")

    @pytest.mark.asyncio
    async def test_list_api_keys(self, client):
        # Create one first
        await client.post(
            "/api/v1/admin/api-keys",
            json={"client_id": "list_test", "name": "Key1"},
        )

        resp = await client.get("/api/v1/admin/api-keys")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_revoke_api_key(self, client):
        create_resp = await client.post(
            "/api/v1/admin/api-keys",
            json={"client_id": "revoke_test"},
        )
        key_id = create_resp.json()["id"]

        resp = await client.delete(f"/api/v1/admin/api-keys/{key_id}")
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_revoke_nonexistent_key(self, client):
        fake_id = str(uuid.uuid4())
        resp = await client.delete(f"/api/v1/admin/api-keys/{fake_id}")
        assert resp.status_code == 404
