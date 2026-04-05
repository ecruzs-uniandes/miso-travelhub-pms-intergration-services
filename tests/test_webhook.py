import pytest
from unittest.mock import patch
from datetime import datetime

pytestmark = pytest.mark.anyio


WEBHOOK_URL = "/api/v1/pms/webhook"


def valid_payload(pms_property_id="HB-001", event_id="evt-001"):
    return {
        "event_id": event_id,
        "event_type": "availability_update",
        "pms_provider": "hotelbeds",
        "pms_property_id": pms_property_id,
        "timestamp": datetime.utcnow().isoformat(),
        "data": {"room_id": "room-1", "available": 5},
    }


async def test_webhook_valid_payload(client, pms_property):
    from tests.conftest import admin_headers
    response = await client.post(WEBHOOK_URL, json=valid_payload(), headers=admin_headers())
    assert response.status_code == 202
    body = response.json()
    assert body["event_id"] == "evt-001"
    assert body["status"] == "queued"


async def test_webhook_invalid_payload(client):
    from tests.conftest import admin_headers
    response = await client.post(WEBHOOK_URL, json={"bad": "data"}, headers=admin_headers())
    assert response.status_code == 422


async def test_webhook_unknown_pms_property(client):
    from tests.conftest import admin_headers
    payload = valid_payload(pms_property_id="UNKNOWN-999", event_id="evt-002")
    response = await client.post(WEBHOOK_URL, json=payload, headers=admin_headers())
    assert response.status_code == 404


async def test_webhook_idempotent_duplicate(client, pms_property):
    from tests.conftest import admin_headers
    payload = valid_payload(event_id="evt-dupe")
    headers = admin_headers()
    # First call
    r1 = await client.post(WEBHOOK_URL, json=payload, headers=headers)
    assert r1.status_code == 202
    # Second call with same event_id
    r2 = await client.post(WEBHOOK_URL, json=payload, headers=headers)
    assert r2.status_code == 202
    assert r2.json()["event_id"] == "evt-dupe"


async def test_webhook_kafka_publish_called(client, pms_property):
    from tests.conftest import admin_headers
    payload = valid_payload(event_id="evt-kafka")
    with patch("app.services.webhook_facade.publish_sync_command") as mock_pub:
        mock_pub.return_value = True
        response = await client.post(WEBHOOK_URL, json=payload, headers=admin_headers())
    assert response.status_code == 202
    mock_pub.assert_called_once()
    call_kwargs = mock_pub.call_args
    assert call_kwargs is not None
    # Verify hotel_id key was passed
    assert "hotel_id" in call_kwargs.kwargs or len(call_kwargs.args) >= 1
