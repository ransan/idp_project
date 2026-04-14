"""WebSocket endpoint for real-time document status updates."""

import asyncio
import json

import redis
import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError

from app.auth import decode_token
from app.config import settings

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/api/v1/ws")
async def websocket_endpoint(ws: WebSocket):
    # Authenticate via query param token
    token = ws.query_params.get("token")
    if not token:
        await ws.close(code=4001, reason="Missing token")
        return

    try:
        payload = decode_token(token)
        client_id = payload.get("client_id")
        if not client_id:
            await ws.close(code=4001, reason="Invalid token")
            return
    except JWTError:
        await ws.close(code=4001, reason="Invalid token")
        return

    await ws.accept()
    logger.info("ws_connected", client_id=client_id)

    channel = f"doc_updates:{client_id}"
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = r.pubsub()
    pubsub.subscribe(channel)

    try:
        while True:
            msg = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.5)
            if msg and msg["type"] == "message":
                await ws.send_text(msg["data"])
            else:
                # Small async sleep to avoid busy-loop
                await asyncio.sleep(0.1)
            # Also handle incoming pings / close frames
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        logger.info("ws_disconnected", client_id=client_id)
    except Exception as e:
        logger.warning("ws_error", client_id=client_id, error=str(e))
    finally:
        pubsub.unsubscribe(channel)
        pubsub.close()
        r.close()
