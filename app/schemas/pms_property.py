from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class PMSPropertyCreate(BaseModel):
    hotel_id: uuid.UUID
    pms_provider: str
    pms_property_id: str
    api_key_hash: Optional[str] = None
    webhook_secret_hash: Optional[str] = None


class PMSPropertyUpdate(BaseModel):
    api_key_hash: Optional[str] = None
    webhook_secret_hash: Optional[str] = None
    status: Optional[str] = None


class PMSPropertyResponse(BaseModel):
    id: uuid.UUID
    hotel_id: uuid.UUID
    pms_provider: str
    pms_property_id: str
    api_key_hash: Optional[str] = None
    webhook_secret_hash: Optional[str] = None
    status: str
    last_sync_at: Optional[datetime] = None
    sync_error_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
