from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class AvailabilityDateEntry(BaseModel):
    date: date
    available_units: int
    rate: Optional[Decimal] = None
    currency: Optional[str] = "USD"


class AvailabilityUpdateData(BaseModel):
    room_id: str
    room_type: str
    dates: list[AvailabilityDateEntry]


class RateEntry(BaseModel):
    date_from: date
    date_to: date
    price: Decimal
    currency: str = "USD"
    discount: Optional[Decimal] = 0


class RateUpdateData(BaseModel):
    room_id: str
    rates: list[RateEntry]


class WebhookPayload(BaseModel):
    event_id: str
    event_type: str
    pms_provider: str
    pms_property_id: str
    timestamp: datetime
    data: dict


class WebhookResponse(BaseModel):
    event_id: str
    status: str
