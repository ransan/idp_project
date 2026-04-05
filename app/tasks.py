import asyncio
from uuid import UUID

import structlog

from app.celery_app import celery_app
from app.database import async_session
from app.services.pipeline import DocumentPipeline, PipelineError

logger = structlog.get_logger(__name__)


def _run_async(coro):
    """Run an async function from a sync Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _process_single(document_id: str) -> None:
    pipeline = DocumentPipeline()
    async with async_session() as db:
        try:
            await pipeline.process_document(UUID(document_id), db)
        except PipelineError:
            # Already logged and status set in pipeline
            pass


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_document_task(self, document_id: str) -> dict:
    logger.info("task_started", document_id=document_id, attempt=self.request.retries)
    try:
        _run_async(_process_single(document_id))
        return {"status": "completed", "document_id": document_id}
    except Exception as exc:
        logger.error("task_failed", document_id=document_id, error=str(exc))
        raise self.retry(exc=exc)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_batch_task(self, document_ids: list[str]) -> dict:
    logger.info("batch_task_started", count=len(document_ids))
    results = []
    for doc_id in document_ids:
        try:
            _run_async(_process_single(doc_id))
            results.append({"document_id": doc_id, "status": "completed"})
        except Exception as e:
            logger.error("batch_item_failed", document_id=doc_id, error=str(e))
            results.append({"document_id": doc_id, "status": "failed", "error": str(e)})
    return {"results": results, "total": len(document_ids)}
