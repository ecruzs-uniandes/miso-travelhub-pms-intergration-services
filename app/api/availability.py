import logging
from typing import Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.disponibilidad import Disponibilidad
from app.models.habitacion import Habitacion
from app.models.sync_event import SyncEvent
from app.schemas.availability import DisponibilidadResponse, SyncStatusResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/availability", response_model=list[DisponibilidadResponse])
async def get_availability(
    hotel_id: Optional[str] = Query(default=None),
    habitacion_id: Optional[str] = Query(default=None),
    date_from: Optional[date] = Query(default=None),
    date_to: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Disponibilidad)

    if habitacion_id:
        query = query.where(Disponibilidad.habitacionId == habitacion_id)
    elif hotel_id:
        query = query.join(Habitacion, Disponibilidad.habitacionId == Habitacion.id).where(
            Habitacion.hotelId == hotel_id
        )

    if date_from:
        query = query.where(Disponibilidad.fecha >= date_from)
    if date_to:
        query = query.where(Disponibilidad.fecha <= date_to)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/sync-status/{event_id}", response_model=SyncStatusResponse)
async def get_sync_status(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SyncEvent).where(SyncEvent.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Sync event not found")
    return event
