import logging
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services import idempotency_service, property_service
from app.services.kafka_producer import publish_sync_command
from app.commands.sync_command import SyncCommand

logger = logging.getLogger(__name__)

# Statuses that indicate event already handled
TERMINAL_STATUSES = {"completed", "queued", "processing"}


async def handle_webhook(db: AsyncSession, payload: WebhookPayload) -> WebhookResponse:
    # Step 1: Resolve hotel_id from PMS property
    pms_prop = await property_service.get_property_by_pms(
        db, payload.pms_provider, payload.pms_property_id
    )
    if not pms_prop:
        raise HTTPException(
            status_code=404,
            detail=f"PMS property not found: {payload.pms_provider}/{payload.pms_property_id}",
        )

    hotel_id = str(pms_prop.hotel_id)

    # Step 2: Check idempotency
    existing = await idempotency_service.check_idempotency(db, payload.event_id)
    if existing and existing.status in TERMINAL_STATUSES:
        logger.info(f"Duplicate event {payload.event_id} with status {existing.status} — skipping")
        return WebhookResponse(event_id=payload.event_id, status=existing.status)

    # Step 3: Compute payload hash and record event
    payload_hash = idempotency_service.compute_payload_hash(payload.data)

    if not existing:
        await idempotency_service.record_event(
            db=db,
            event_id=payload.event_id,
            pms_provider=payload.pms_provider,
            event_type=payload.event_type,
            hotel_id=hotel_id,
            payload_hash=payload_hash,
        )

    # Step 4: Build SyncCommand
    command = SyncCommand.create(
        event_id=payload.event_id,
        event_type=payload.event_type,
        pms_provider=payload.pms_provider,
        hotel_id=hotel_id,
        pms_property_id=payload.pms_property_id,
        timestamp=payload.timestamp,
        data=payload.data,
    )

    # Step 5: Publish to Kafka
    published = publish_sync_command(hotel_id=hotel_id, message=command.to_json())

    if not published:
        await idempotency_service.update_event_status(db, payload.event_id, "failed")
        raise HTTPException(status_code=503, detail="Failed to enqueue sync command")

    # Step 6: Update status to queued
    await idempotency_service.update_event_status(db, payload.event_id, "queued")

    return WebhookResponse(event_id=payload.event_id, status="queued")
