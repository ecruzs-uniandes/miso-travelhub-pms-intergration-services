from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
import uuid


class AvailabilityResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    fecha: date
    unidades_disponibles: int
    unidades_reservadas: int
    ultima_actualizacion: Optional[datetime] = None
    fuente_actualizacion: Optional[str] = None

    model_config = {"from_attributes": True}


class AvailabilityQuery(BaseModel):
    hotel_id: Optional[uuid.UUID] = None
    room_id: Optional[uuid.UUID] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class SyncStatusResponse(BaseModel):
    event_id: str
    status: str
    pms_provider: str
    event_type: str
    retry_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
