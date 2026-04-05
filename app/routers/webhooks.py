from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_client
from app.database import get_db
from app.models import WebhookConfig
from app.schemas import WebhookConfigRequest, WebhookConfigResponse

router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


@router.post("/configure", response_model=WebhookConfigResponse, status_code=201)
async def configure_webhook(
    payload: WebhookConfigRequest,
    db: AsyncSession = Depends(get_db),
    client: dict = Depends(get_current_client),
):
    client_id = client["client_id"]

    # Upsert: update if exists, create if not
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.client_id == client_id)
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.url = payload.url
        existing.is_active = True
        await db.flush()
        return WebhookConfigResponse(
            id=existing.id,
            client_id=existing.client_id,
            url=existing.url,
            is_active=existing.is_active,
        )

    webhook = WebhookConfig(
        client_id=client_id,
        url=payload.url,
    )
    db.add(webhook)
    await db.flush()

    return WebhookConfigResponse(
        id=webhook.id,
        client_id=webhook.client_id,
        url=webhook.url,
        is_active=webhook.is_active,
    )


@router.get("/", response_model=WebhookConfigResponse)
async def get_webhook(
    db: AsyncSession = Depends(get_db),
    client: dict = Depends(get_current_client),
):
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.client_id == client["client_id"])
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="No webhook configured")

    return WebhookConfigResponse(
        id=webhook.id,
        client_id=webhook.client_id,
        url=webhook.url,
        is_active=webhook.is_active,
    )


@router.delete("/", status_code=204)
async def delete_webhook(
    db: AsyncSession = Depends(get_db),
    client: dict = Depends(get_current_client),
):
    result = await db.execute(
        select(WebhookConfig).where(WebhookConfig.client_id == client["client_id"])
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=404, detail="No webhook configured")

    webhook.is_active = False
    await db.flush()
