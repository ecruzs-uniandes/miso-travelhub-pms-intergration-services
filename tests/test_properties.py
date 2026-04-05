import uuid
import pytest

pytestmark = pytest.mark.anyio

PROPERTIES_URL = "/api/v1/pms/properties"


async def test_create_pms_property(client, hotel):
    from tests.conftest import admin_headers
    payload = {
        "hotel_id": str(hotel.id),
        "pms_provider": "travelclick",
        "pms_property_id": "TC-001",
    }
    response = await client.post(PROPERTIES_URL, json=payload, headers=admin_headers())
    assert response.status_code == 201
    body = response.json()
    assert body["pms_provider"] == "travelclick"
    assert body["pms_property_id"] == "TC-001"
    assert body["status"] == "active"


async def test_list_pms_properties_by_hotel(client, hotel, pms_property):
    from tests.conftest import admin_headers
    response = await client.get(
        PROPERTIES_URL, params={"hotel_id": str(hotel.id)}, headers=admin_headers()
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body) >= 1
    assert any(p["hotel_id"] == str(hotel.id) for p in body)


async def test_create_duplicate_pms_property(client, hotel, pms_property):
    from tests.conftest import admin_headers
    # pms_property fixture already has hotelbeds/HB-001
    payload = {
        "hotel_id": str(hotel.id),
        "pms_provider": "hotelbeds",
        "pms_property_id": "HB-001",
    }
    response = await client.post(PROPERTIES_URL, json=payload, headers=admin_headers())
    assert response.status_code == 409


async def test_update_pms_property(client, hotel, pms_property):
    from tests.conftest import admin_headers
    url = f"{PROPERTIES_URL}/{pms_property.id}"
    payload = {"status": "inactive"}
    response = await client.put(url, json=payload, headers=admin_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


async def test_delete_pms_property(client, hotel, pms_property):
    from tests.conftest import admin_headers
    url = f"{PROPERTIES_URL}/{pms_property.id}"
    response = await client.delete(url, headers=admin_headers())
    assert response.status_code == 200
    assert response.json()["status"] == "inactive"


async def test_get_pms_property_not_found(client):
    from tests.conftest import admin_headers
    fake_id = str(uuid.uuid4())
    response = await client.get(f"{PROPERTIES_URL}/{fake_id}", headers=admin_headers())
    assert response.status_code == 404
