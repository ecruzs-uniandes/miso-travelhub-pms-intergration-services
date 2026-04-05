import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, patch

from app.main import app
from app.database import Base, get_db
from app.models.hotel import Hotel
from app.models.pms_property import PMSProperty
from app.models.room import Room
from app.models.availability import Availability

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(test_engine):
    TestSessionLocal = sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.services.kafka_producer.publish_sync_command", return_value=True):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def hotel(db_session):
    h = Hotel(
        id=uuid.uuid4(),
        nombre="Hotel Test",
        ciudad="Bogota",
        pais="CO",
        pms_proveedor="hotelbeds",
    )
    db_session.add(h)
    await db_session.commit()
    await db_session.refresh(h)
    return h


@pytest_asyncio.fixture(scope="function")
async def pms_property(db_session, hotel):
    prop = PMSProperty(
        id=uuid.uuid4(),
        hotel_id=hotel.id,
        pms_provider="hotelbeds",
        pms_property_id="HB-001",
        webhook_secret_hash="test-secret",
        status="active",
    )
    db_session.add(prop)
    await db_session.commit()
    await db_session.refresh(prop)
    return prop


@pytest_asyncio.fixture(scope="function")
async def room(db_session, hotel):
    r = Room(
        id=uuid.uuid4(),
        hotel_id=hotel.id,
        tipo="Standard",
        capacidad_maxima=2,
    )
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


@pytest_asyncio.fixture(scope="function")
async def availability_record(db_session, room):
    from datetime import date
    a = Availability(
        id=uuid.uuid4(),
        room_id=room.id,
        fecha=date(2026, 6, 1),
        unidades_disponibles=5,
        unidades_reservadas=1,
        fuente_actualizacion="pms_webhook",
    )
    db_session.add(a)
    await db_session.commit()
    await db_session.refresh(a)
    return a


def admin_headers():
    """Returns headers with a hotel_admin JWT (unsigned, for testing)."""
    import base64, json
    header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.b64encode(json.dumps({"sub": "user-1", "role": "hotel_admin"}).encode()).decode().rstrip("=")
    token = f"{header}.{payload}.fakesig"
    return {"Authorization": f"Bearer {token}"}


def traveler_headers():
    import base64, json
    header = base64.b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
    payload = base64.b64encode(json.dumps({"sub": "user-2", "role": "traveler"}).encode()).decode().rstrip("=")
    token = f"{header}.{payload}.fakesig"
    return {"Authorization": f"Bearer {token}"}
