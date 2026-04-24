import uuid
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from app.models.pms_property import PMSProperty
from app.schemas.pms_property import PMSPropertyCreate, PMSPropertyUpdate

logger = logging.getLogger(__name__)


async def create_property(db: AsyncSession, data: PMSPropertyCreate) -> PMSProperty:
    prop = PMSProperty(
        hotel_id=data.hotel_id,
        pms_provider=data.pms_provider,
        pms_property_id=data.pms_property_id,
        api_key_hash=data.api_key_hash,
        webhook_secret_hash=data.webhook_secret_hash,
    )
    db.add(prop)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="PMS property already exists")
    return prop


async def list_properties(
    db: AsyncSession, hotel_id: Optional[uuid.UUID] = None
) -> list[PMSProperty]:
    query = select(PMSProperty)
    if hotel_id:
        query = query.where(PMSProperty.hotel_id == hotel_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_property(db: AsyncSession, property_id: uuid.UUID) -> PMSProperty:
    result = await db.execute(
        select(PMSProperty).where(PMSProperty.id == property_id)
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="PMS property not found")
    return prop


async def get_property_by_pms(
    db: AsyncSession, pms_provider: str, pms_property_id: str
) -> Optional[PMSProperty]:
    result = await db.execute(
        select(PMSProperty).where(
            PMSProperty.pms_provider == pms_provider,
            PMSProperty.pms_property_id == pms_property_id,
            PMSProperty.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def update_property(
    db: AsyncSession, property_id: uuid.UUID, data: PMSPropertyUpdate
) -> PMSProperty:
    prop = await get_property(db, property_id)
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(prop, field, value)
    await db.flush()
    await db.refresh(prop)
    return prop


async def delete_property(db: AsyncSession, property_id: uuid.UUID) -> PMSProperty:
    prop = await get_property(db, property_id)
    prop.status = "inactive"
    await db.flush()
    await db.refresh(prop)
    return prop
