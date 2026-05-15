import pytest
from datetime import datetime
from unittest.mock import patch

pytestmark = pytest.mark.anyio

AVAILABILITY_URL = "/api/v1/pms/availability"
WEBHOOK_URL = "/api/v1/pms/webhook"


async def test_get_availability_by_hotel_and_dates(client, hotel, availability_record):
    from tests.conftest import admin_headers
    response = await client.get(
        AVAILABILITY_URL,
        params={
            "hotel_id": str(hotel.id),
            "date_from": "2026-05-01",
            "date_to": "2026-07-01",
        },
        headers=admin_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert body[0]["unidadesDisponibles"] == 5


async def test_get_availability_no_results(client, hotel):
    from tests.conftest import admin_headers
    response = await client.get(
        AVAILABILITY_URL,
        params={
            "hotel_id": str(hotel.id),
            "date_from": "2030-01-01",
            "date_to": "2030-01-31",
        },
        headers=admin_headers(),
    )
    assert response.status_code == 200
    assert response.json() == []


async def test_get_sync_status(client, pms_property):
    from tests.conftest import admin_headers

    # Create an event first via webhook
    payload = {
        "event_id": "status-check-001",
        "event_type": "availability_update",
        "pms_provider": "hotelbeds",
        "pms_property_id": "HB-001",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {"room_id": "r1"},
    }
    await client.post(WEBHOOK_URL, json=payload, headers=admin_headers())

    response = await client.get(
        "/api/v1/pms/sync-status/status-check-001",
        headers=admin_headers(),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == "status-check-001"
    assert body["status"] in ("queued", "received")


async def test_get_sync_status_not_found(client):
    from tests.conftest import admin_headers
    response = await client.get(
        "/api/v1/pms/sync-status/nonexistent-id",
        headers=admin_headers(),
    )
    assert response.status_code == 404
