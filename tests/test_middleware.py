import base64
import json
import pytest
from datetime import datetime

pytestmark = pytest.mark.anyio

WEBHOOK_URL = "/api/v1/pms/webhook"
AVAILABILITY_URL = "/api/v1/pms/availability"
PROPERTIES_URL = "/api/v1/pms/properties"


def make_token(role: str, sub: str = "user-test") -> str:
    header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.b64encode(json.dumps({"sub": sub, "role": role}).encode()).decode().rstrip("=")
    return f"{header}.{payload}.fakesig"


def auth(role: str) -> dict:
    return {"Authorization": f"Bearer {make_token(role)}"}


async def test_rbac_hotel_admin_allowed(client, pms_property):
    response = await client.get(PROPERTIES_URL, headers=auth("hotel_admin"))
    assert response.status_code == 200


async def test_rbac_traveler_only_get_availability(client, hotel):
    # GET availability — allowed for traveler
    response = await client.get(
        AVAILABILITY_URL,
        params={"hotel_id": str(hotel.id)},
        headers=auth("traveler"),
    )
    assert response.status_code == 200

    # POST webhook — forbidden for traveler
    payload = {
        "event_id": "rbac-test-001",
        "event_type": "availability_update",
        "pms_provider": "hotelbeds",
        "pms_property_id": "HB-001",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {},
    }
    response = await client.post(WEBHOOK_URL, json=payload, headers=auth("traveler"))
    assert response.status_code == 403


async def test_rbac_no_token(client):
    response = await client.get(PROPERTIES_URL)
    assert response.status_code == 401


async def test_rate_limit_exceeded(client):
    """Hit the rate limiter with 61 requests."""
    # Use a unique user so other tests don't interfere
    headers = auth("hotel_admin")
    # Override rate-limit bucket by using unique sub
    unique_token = make_token("hotel_admin", sub="rate-limit-test-user")
    headers = {"Authorization": f"Bearer {unique_token}"}

    responses = []
    for _ in range(61):
        r = await client.get(PROPERTIES_URL, headers=headers)
        responses.append(r.status_code)

    assert 429 in responses


async def test_platform_admin_allowed(client):
    response = await client.get(PROPERTIES_URL, headers=auth("platform_admin"))
    assert response.status_code == 200
