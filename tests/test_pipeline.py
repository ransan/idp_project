import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models import DocStatus, Document, WebhookConfig
from app.schemas import LLMResult, ParseResult
from app.services.pipeline import DocumentPipeline, PipelineError


@pytest.fixture
def mock_storage():
    with patch("app.services.pipeline.storage") as mock_st:
        mock_st.get_local_path.return_value = "/tmp/test.pdf"
        yield mock_st


@pytest.fixture
def mock_parser():
    with patch("app.services.pipeline.DocumentParser") as MockParser:
        parser_instance = MockParser.return_value
        parser_instance.parse.return_value = ParseResult(
            text="Invoice #12345 from Acme Corp. Total: $1,500.",
            page_count=2,
            method="pymupdf",
        )
        yield parser_instance


@pytest.fixture
def mock_llm():
    with patch("app.services.pipeline.LLMService") as MockLLM:
        llm_instance = MockLLM.return_value
        llm_instance.analyze_document.return_value = LLMResult(
            category="invoice",
            confidence=0.95,
            summary="Invoice from Acme Corp for $1,500.",
            extracted_data={"vendor": "Acme Corp", "total_amount": 1500.0},
            key_entities={"organizations": ["Acme Corp"]},
            flags=["Due within 30 days"],
        )
        yield llm_instance


@pytest_asyncio.fixture
async def doc_in_db(db_session):
    """Insert a test document into the database."""
    doc = Document(
        filename="test.pdf",
        original_name="invoice.pdf",
        file_size=2048,
        mime_type="application/pdf",
        storage_path="/tmp/test.pdf",
        client_id="test_client",
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


class TestDocumentPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_success(self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm):
        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()

        assert doc.status == DocStatus.COMPLETED
        assert doc.raw_text is not None
        assert doc.page_count == 2
        assert doc.category == "invoice"
        assert doc.confidence == 0.95
        assert doc.summary is not None
        assert doc.extracted_data is not None
        assert doc.key_entities is not None
        assert doc.flags is not None
        assert doc.processed_at is not None
        assert doc.processing_time_ms is not None
        assert doc.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_status_progression(self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm):
        """Document status should progress through uploaded -> parsing -> processing -> completed."""
        statuses_seen = []

        original_commit = db_session.commit

        async def tracking_commit():
            result = await db_session.execute(
                select(Document.status).where(Document.id == doc_in_db.id)
            )
            status = result.scalar_one()
            statuses_seen.append(status)
            await original_commit()

        db_session.commit = tracking_commit

        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        await pipeline.process_document(doc_in_db.id, db_session)

        # Should have seen: parsing, parsing(after text stored), processing, completed
        status_values = [s.value if hasattr(s, "value") else s for s in statuses_seen]
        assert "parsing" in status_values
        assert "processing" in status_values
        assert "completed" in status_values

    @pytest.mark.asyncio
    async def test_parser_failure_sets_failed(self, db_session, doc_in_db, mock_storage, mock_llm):
        from app.services.parser import ParserError

        with patch("app.services.pipeline.DocumentParser") as MockParser:
            parser_instance = MockParser.return_value
            parser_instance.parse.side_effect = ParserError("Corrupted file")

            pipeline = DocumentPipeline()
            pipeline.parser = parser_instance
            pipeline.llm_service = mock_llm

            with pytest.raises(PipelineError):
                await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()
        assert doc.status == DocStatus.FAILED
        assert "Corrupted file" in doc.error_message

    @pytest.mark.asyncio
    async def test_llm_failure_sets_failed(self, db_session, doc_in_db, mock_storage, mock_parser):
        from app.services.llm import LLMServiceError

        with patch("app.services.pipeline.LLMService") as MockLLM:
            llm_instance = MockLLM.return_value
            llm_instance.analyze_document.side_effect = LLMServiceError("API timeout")

            pipeline = DocumentPipeline()
            pipeline.parser = mock_parser
            pipeline.llm_service = llm_instance

            with pytest.raises(PipelineError):
                await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()
        assert doc.status == DocStatus.FAILED
        assert "API timeout" in doc.error_message

    @pytest.mark.asyncio
    async def test_document_not_found(self, db_session):
        pipeline = DocumentPipeline()
        fake_id = uuid.uuid4()
        with pytest.raises(PipelineError, match="not found"):
            await pipeline.process_document(fake_id, db_session)

    @pytest.mark.asyncio
    async def test_processing_time_recorded(self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm):
        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()
        assert doc.processing_time_ms is not None
        assert doc.processing_time_ms >= 0

    @pytest.mark.asyncio
    async def test_all_llm_results_stored(self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm):
        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()

        assert doc.category == "invoice"
        assert doc.confidence == 0.95
        assert doc.summary == "Invoice from Acme Corp for $1,500."
        assert doc.extracted_data["vendor"] == "Acme Corp"
        assert doc.key_entities["organizations"] == ["Acme Corp"]
        assert "Due within 30 days" in doc.flags

    @pytest.mark.asyncio
    async def test_webhook_sent_on_completion(self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm):
        # Add webhook config
        wh = WebhookConfig(
            client_id="test_client",
            url="https://example.com/webhook",
        )
        db_session.add(wh)
        await db_session.flush()

        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        with patch("app.services.pipeline.httpx.AsyncClient") as MockClient:
            mock_response = MagicMock(status_code=200)
            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            await pipeline.process_document(doc_in_db.id, db_session)

            mock_client_instance.post.assert_called_once()
            call_args = mock_client_instance.post.call_args
            assert call_args[0][0] == "https://example.com/webhook"
            payload = call_args[1]["json"]
            assert payload["status"] == "completed"

    @pytest.mark.asyncio
    async def test_webhook_failure_does_not_crash_pipeline(
        self, db_session, doc_in_db, mock_storage, mock_parser, mock_llm
    ):
        wh = WebhookConfig(
            client_id="test_client",
            url="https://example.com/webhook",
        )
        db_session.add(wh)
        await db_session.flush()

        pipeline = DocumentPipeline()
        pipeline.parser = mock_parser
        pipeline.llm_service = mock_llm

        with patch("app.services.pipeline.httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.post.side_effect = Exception("Connection refused")
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=None)
            MockClient.return_value = mock_client_instance

            # Should not raise
            await pipeline.process_document(doc_in_db.id, db_session)

        result = await db_session.execute(
            select(Document).where(Document.id == doc_in_db.id)
        )
        doc = result.scalar_one()
        assert doc.status == DocStatus.COMPLETED
