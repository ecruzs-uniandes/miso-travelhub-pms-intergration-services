import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from app.services import idempotency_service
from app.models.sync_event import SyncEvent

pytestmark = pytest.mark.anyio


async def test_new_event_is_recorded(db_session, hotel):
    event = await idempotency_service.record_event(
        db=db_session,
        event_id="new-event-001",
        pms_provider="hotelbeds",
        event_type="availability_update",
        hotel_id=str(hotel.id),
        payload_hash="abc123",
    )
    await db_session.commit()
    assert event.event_id == "new-event-001"
    assert event.status == "received"


async def test_duplicate_event_returns_existing(db_session, hotel):
    await idempotency_service.record_event(
        db=db_session,
        event_id="dup-event-001",
        pms_provider="hotelbeds",
        event_type="availability_update",
        hotel_id=str(hotel.id),
        payload_hash="hash1",
    )
    await db_session.commit()

    existing = await idempotency_service.check_idempotency(db_session, "dup-event-001")
    assert existing is not None
    assert existing.event_id == "dup-event-001"
    assert existing.status == "received"


async def test_concurrent_duplicate_events(db_session, hotel):
    """Unique constraint on event_id prevents duplicate inserts."""
    await idempotency_service.record_event(
        db=db_session,
        event_id="concurrent-event-001",
        pms_provider="hotelbeds",
        event_type="availability_update",
        hotel_id=str(hotel.id),
        payload_hash="hash2",
    )
    await db_session.commit()

    # Attempt to insert duplicate should raise IntegrityError
    dup = SyncEvent(
        event_id="concurrent-event-001",
        pms_provider="hotelbeds",
        event_type="availability_update",
        hotel_id=hotel.id,
        payload_hash="hash2",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


async def test_update_event_status(db_session, hotel):
    await idempotency_service.record_event(
        db=db_session,
        event_id="status-event-001",
        pms_provider="hotelbeds",
        event_type="availability_update",
        hotel_id=str(hotel.id),
        payload_hash="hash3",
    )
    await db_session.commit()

    await idempotency_service.update_event_status(db_session, "status-event-001", "queued")
    await db_session.commit()

    event = await idempotency_service.check_idempotency(db_session, "status-event-001")
    assert event.status == "queued"
