import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.pms_property import PMSPropertyCreate, PMSPropertyUpdate, PMSPropertyResponse
from app.services import property_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/properties", response_model=PMSPropertyResponse, status_code=201)
async def create_pms_property(
    data: PMSPropertyCreate,
    db: AsyncSession = Depends(get_db),
):
    prop = await property_service.create_property(db, data)
    return prop


@router.get("/properties", response_model=list[PMSPropertyResponse])
async def list_pms_properties(
    hotel_id: Optional[uuid.UUID] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    return await property_service.list_properties(db, hotel_id)


@router.get("/properties/{property_id}", response_model=PMSPropertyResponse)
async def get_pms_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await property_service.get_property(db, property_id)


@router.put("/properties/{property_id}", response_model=PMSPropertyResponse)
async def update_pms_property(
    property_id: uuid.UUID,
    data: PMSPropertyUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await property_service.update_property(db, property_id, data)


@router.delete("/properties/{property_id}", response_model=PMSPropertyResponse)
async def delete_pms_property(
    property_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await property_service.delete_property(db, property_id)
