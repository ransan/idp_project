import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas import (
    APIKeyCreateRequest,
    BatchUploadResponse,
    DocumentFilterParams,
    DocumentListResponse,
    DocumentResponse,
    DocumentSummary,
    DocumentUploadResponse,
    HealthResponse,
    LLMResult,
    ParseResult,
    ReprocessResponse,
    StatsResponse,
    StatusCount,
    CategoryCount,
    WebhookConfigRequest,
)


class TestHealthResponse:
    def test_serialization(self):
        h = HealthResponse(status="ok", version="0.1.0")
        assert h.status == "ok"
        assert h.version == "0.1.0"


class TestDocumentUploadResponse:
    def test_serialization(self):
        doc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        r = DocumentUploadResponse(
            id=doc_id,
            filename="test.pdf",
            original_name="invoice.pdf",
            status="uploaded",
            created_at=now,
        )
        data = r.model_dump()
        assert data["id"] == doc_id
        assert data["status"] == "uploaded"


class TestDocumentResponse:
    def test_full_payload(self):
        doc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        r = DocumentResponse(
            id=doc_id,
            filename="test.pdf",
            original_name="invoice.pdf",
            file_size=2048,
            mime_type="application/pdf",
            status="completed",
            category="invoice",
            confidence=0.95,
            summary="Test summary",
            extracted_data={"vendor": "Acme"},
            key_entities={"people": ["John"]},
            flags=["deadline"],
            client_id="client_1",
            tags=["finance"],
            created_at=now,
            processed_at=now,
            processing_time_ms=3400,
        )
        assert r.category == "invoice"
        assert r.confidence == 0.95

    def test_optional_fields_none(self):
        doc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        r = DocumentResponse(
            id=doc_id,
            filename="test.pdf",
            original_name="test.pdf",
            status="uploaded",
            created_at=now,
        )
        assert r.category is None
        assert r.summary is None
        assert r.extracted_data is None


class TestDocumentFilterParams:
    def test_defaults(self):
        p = DocumentFilterParams()
        assert p.page == 1
        assert p.size == 20
        assert p.status is None

    def test_valid_page(self):
        p = DocumentFilterParams(page=5, size=50)
        assert p.page == 5
        assert p.size == 50

    def test_invalid_page_rejected(self):
        with pytest.raises(ValidationError):
            DocumentFilterParams(page=0)

    def test_size_too_large_rejected(self):
        with pytest.raises(ValidationError):
            DocumentFilterParams(size=101)

    def test_negative_size_rejected(self):
        with pytest.raises(ValidationError):
            DocumentFilterParams(size=-1)


class TestBatchUploadResponse:
    def test_serialization(self):
        now = datetime.now(timezone.utc)
        docs = [
            DocumentUploadResponse(
                id=uuid.uuid4(),
                filename=f"file{i}.pdf",
                original_name=f"doc{i}.pdf",
                status="uploaded",
                created_at=now,
            )
            for i in range(3)
        ]
        r = BatchUploadResponse(documents=docs, total=3)
        assert r.total == 3
        assert len(r.documents) == 3


class TestStatsResponse:
    def test_serialization(self):
        r = StatsResponse(
            total_documents=100,
            by_status=[StatusCount(status="completed", count=80)],
            by_category=[CategoryCount(category="invoice", count=50)],
        )
        assert r.total_documents == 100


class TestReprocessResponse:
    def test_serialization(self):
        r = ReprocessResponse(
            id=uuid.uuid4(),
            status="uploaded",
            message="Queued",
        )
        assert r.status == "uploaded"


class TestWebhookConfigRequest:
    def test_valid_url(self):
        w = WebhookConfigRequest(url="https://example.com/hook")
        assert w.url == "https://example.com/hook"

    def test_url_too_long(self):
        with pytest.raises(ValidationError):
            WebhookConfigRequest(url="x" * 2049)


class TestAPIKeyCreateRequest:
    def test_valid(self):
        r = APIKeyCreateRequest(client_id="client_1", name="My Key")
        assert r.client_id == "client_1"
        assert r.rate_limit == 100

    def test_empty_client_id_rejected(self):
        with pytest.raises(ValidationError):
            APIKeyCreateRequest(client_id="")


class TestLLMResult:
    def test_defaults(self):
        r = LLMResult()
        assert r.category == "unknown"
        assert r.confidence == 0.0
        assert r.extracted_data == {}
        assert r.flags == []

    def test_full(self):
        r = LLMResult(
            category="invoice",
            confidence=0.95,
            summary="Test",
            extracted_data={"vendor": "Acme"},
            key_entities={"people": []},
            flags=["deadline"],
        )
        assert r.category == "invoice"


class TestParseResult:
    def test_defaults(self):
        r = ParseResult(text="Hello")
        assert r.page_count == 0
        assert r.method == ""

    def test_full(self):
        r = ParseResult(text="Content", page_count=5, method="pymupdf")
        assert r.page_count == 5
