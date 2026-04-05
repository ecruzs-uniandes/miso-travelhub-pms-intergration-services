import hashlib
import json
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.sync_event import SyncEvent

logger = logging.getLogger(__name__)


def compute_payload_hash(data: dict) -> str:
    payload_str = json.dumps(data, sort_keys=True, default=str)
    return hashlib.sha256(payload_str.encode()).hexdigest()


async def check_idempotency(db: AsyncSession, event_id: str) -> SyncEvent | None:
    result = await db.execute(
        select(SyncEvent).where(SyncEvent.event_id == event_id)
    )
    return result.scalar_one_or_none()


async def record_event(
    db: AsyncSession,
    event_id: str,
    pms_provider: str,
    event_type: str,
    hotel_id: str,
    payload_hash: str,
) -> SyncEvent:
    sync_event = SyncEvent(
        event_id=event_id,
        pms_provider=pms_provider,
        event_type=event_type,
        hotel_id=hotel_id,
        payload_hash=payload_hash,
        status="received",
    )
    db.add(sync_event)
    await db.flush()
    return sync_event


async def update_event_status(
    db: AsyncSession, event_id: str, status: str
) -> None:
    result = await db.execute(
        select(SyncEvent).where(SyncEvent.event_id == event_id)
    )
    sync_event = result.scalar_one_or_none()
    if sync_event:
        sync_event.status = status
        await db.flush()
