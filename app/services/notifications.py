"""Redis Pub/Sub notifications for real-time document status updates."""

import json

import redis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def publish_document_update(client_id: str, payload: dict) -> None:
    """Publish a document status change to the client's channel."""
    channel = f"doc_updates:{client_id}"
    try:
        _get_redis().publish(channel, json.dumps(payload))
    except Exception as e:
        logger.warning("notification_publish_failed", channel=channel, error=str(e))
