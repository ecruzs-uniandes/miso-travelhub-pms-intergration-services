from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime


class DisponibilidadResponse(BaseModel):
    id: str
    habitacionId: str
    fecha: date
    unidadesDisponibles: int
    unidadesReservadas: int
    ultimaActualizacion: Optional[datetime] = None
    fuenteActualizacion: Optional[str] = None

    model_config = {"from_attributes": True}


class DisponibilidadQuery(BaseModel):
    hotel_id: Optional[str] = None
    habitacionId: Optional[str] = None
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
