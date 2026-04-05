import time
from datetime import datetime, timezone
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DocStatus, Document, WebhookConfig
from app.schemas import LLMResult
from app.services.llm import LLMService, LLMServiceError
from app.services.parser import DocumentParser, ParserError
from app.services.storage import storage

logger = structlog.get_logger(__name__)


class PipelineError(Exception):
    pass


class DocumentPipeline:
    def __init__(self):
        self.parser = DocumentParser()
        self.llm_service = LLMService()

    async def process_document(self, document_id: UUID, db: AsyncSession) -> None:
        start_time = time.monotonic()

        # Load document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            logger.error("document_not_found", document_id=str(document_id))
            raise PipelineError(f"Document {document_id} not found")

        try:
            # --- Stage 1: Parse ---
            doc.status = DocStatus.PARSING
            await db.commit()

            # Resolve a local file path (downloads from MinIO if needed)
            local_path = storage.get_local_path(doc.storage_path)

            logger.info("parsing_started", document_id=str(document_id), file=local_path)
            parse_result = self.parser.parse(local_path, doc.mime_type)

            doc.raw_text = parse_result.text
            doc.page_count = parse_result.page_count
            await db.commit()

            # --- Stage 2: LLM Analysis ---
            doc.status = DocStatus.PROCESSING
            await db.commit()

            logger.info("llm_processing_started", document_id=str(document_id))
            llm_result: LLMResult = self.llm_service.analyze_document(parse_result.text)

            # Store results
            doc.category = llm_result.category
            doc.confidence = llm_result.confidence
            doc.summary = llm_result.summary
            doc.extracted_data = llm_result.extracted_data
            doc.key_entities = llm_result.key_entities
            doc.flags = llm_result.flags

            # Mark completed
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            doc.status = DocStatus.COMPLETED
            doc.processed_at = datetime.now(timezone.utc)
            doc.processing_time_ms = elapsed_ms
            await db.commit()

            logger.info(
                "processing_completed",
                document_id=str(document_id),
                category=llm_result.category,
                confidence=llm_result.confidence,
                elapsed_ms=elapsed_ms,
            )

            # Fire webhook if configured
            await self._send_webhook(doc, db)

        except (ParserError, LLMServiceError) as e:
            doc.status = DocStatus.FAILED
            doc.error_message = str(e)
            await db.commit()
            logger.error(
                "processing_failed",
                document_id=str(document_id),
                error=str(e),
            )
            # Send failure webhook
            await self._send_webhook(doc, db)
            raise PipelineError(str(e)) from e

        except Exception as e:
            doc.status = DocStatus.FAILED
            doc.error_message = f"Unexpected error: {e}"
            await db.commit()
            logger.error(
                "processing_unexpected_error",
                document_id=str(document_id),
                error=str(e),
            )
            await self._send_webhook(doc, db)
            raise PipelineError(str(e)) from e

    async def _send_webhook(self, doc: Document, db: AsyncSession) -> None:
        if not doc.client_id:
            return

        result = await db.execute(
            select(WebhookConfig).where(
                WebhookConfig.client_id == doc.client_id,
                WebhookConfig.is_active == True,  # noqa: E712
            )
        )
        webhook = result.scalar_one_or_none()
        if not webhook:
            return

        payload = {
            "document_id": str(doc.id),
            "status": doc.status.value if isinstance(doc.status, DocStatus) else doc.status,
            "category": doc.category.value if doc.category and hasattr(doc.category, "value") else doc.category,
            "original_name": doc.original_name,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook.url, json=payload)
                logger.info(
                    "webhook_sent",
                    client_id=doc.client_id,
                    url=webhook.url,
                    status_code=response.status_code,
                )
        except Exception as e:
            logger.warning(
                "webhook_failed",
                client_id=doc.client_id,
                url=webhook.url,
                error=str(e),
            )
