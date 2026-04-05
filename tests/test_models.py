import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from app.models import APIKey, Base, DocCategory, DocStatus, Document, WebhookConfig


class TestDocStatusEnum:
    def test_all_values(self):
        assert DocStatus.UPLOADED.value == "uploaded"
        assert DocStatus.PARSING.value == "parsing"
        assert DocStatus.PROCESSING.value == "processing"
        assert DocStatus.COMPLETED.value == "completed"
        assert DocStatus.FAILED.value == "failed"

    def test_enum_count(self):
        assert len(DocStatus) == 5


class TestDocCategoryEnum:
    def test_all_values(self):
        assert DocCategory.INVOICE.value == "invoice"
        assert DocCategory.CONTRACT.value == "contract"
        assert DocCategory.REPORT.value == "report"
        assert DocCategory.LEGAL_BRIEF.value == "legal_brief"
        assert DocCategory.FINANCIAL_STATEMENT.value == "financial_statement"
        assert DocCategory.SHIPPING_MANIFEST.value == "shipping_manifest"
        assert DocCategory.UNKNOWN.value == "unknown"

    def test_enum_count(self):
        assert len(DocCategory) == 7


class TestDocumentModel:
    @pytest.mark.asyncio
    async def test_create_document(self, db_session):
        doc = Document(
            filename="test.pdf",
            original_name="invoice.pdf",
            file_size=2048,
            mime_type="application/pdf",
            storage_path="/uploads/test.pdf",
            client_id="client_1",
        )
        db_session.add(doc)
        await db_session.flush()

        assert doc.id is not None
        assert doc.status == DocStatus.UPLOADED
        assert doc.created_at is not None

    @pytest.mark.asyncio
    async def test_document_defaults(self, db_session):
        doc = Document(
            filename="a.pdf",
            original_name="a.pdf",
            storage_path="/uploads/a.pdf",
        )
        db_session.add(doc)
        await db_session.flush()

        assert doc.status == DocStatus.UPLOADED
        assert doc.error_message is None
        assert doc.raw_text is None
        assert doc.category is None
        assert doc.confidence is None
        assert doc.summary is None
        assert doc.extracted_data is None
        assert doc.key_entities is None
        assert doc.flags is None
        assert doc.processed_at is None

    @pytest.mark.asyncio
    async def test_document_jsonb_fields(self, db_session):
        doc = Document(
            filename="b.pdf",
            original_name="b.pdf",
            storage_path="/uploads/b.pdf",
            extracted_data={"vendor": "Acme"},
            key_entities={"people": ["John"]},
            flags=["deadline approaching"],
            tags=["finance", "urgent"],
        )
        db_session.add(doc)
        await db_session.flush()

        assert doc.extracted_data == {"vendor": "Acme"}
        assert doc.key_entities == {"people": ["John"]}
        assert doc.flags == ["deadline approaching"]
        assert doc.tags == ["finance", "urgent"]

    @pytest.mark.asyncio
    async def test_document_status_update(self, db_session):
        doc = Document(
            filename="c.pdf",
            original_name="c.pdf",
            storage_path="/uploads/c.pdf",
        )
        db_session.add(doc)
        await db_session.flush()

        doc.status = DocStatus.COMPLETED
        doc.category = DocCategory.INVOICE
        doc.confidence = 0.97
        await db_session.flush()

        assert doc.status == DocStatus.COMPLETED
        assert doc.category == DocCategory.INVOICE
        assert doc.confidence == 0.97


class TestAPIKeyModel:
    @pytest.mark.asyncio
    async def test_create_api_key(self, db_session):
        key = APIKey(
            key_hash="hashed_value_here",
            client_id="test_client",
            name="Test Key",
            rate_limit=50,
        )
        db_session.add(key)
        await db_session.flush()

        assert key.id is not None
        assert key.is_active is True
        assert key.rate_limit == 50


class TestWebhookConfigModel:
    @pytest.mark.asyncio
    async def test_create_webhook(self, db_session):
        wh = WebhookConfig(
            client_id="test_client",
            url="https://example.com/webhook",
        )
        db_session.add(wh)
        await db_session.flush()

        assert wh.id is not None
        assert wh.is_active is True
