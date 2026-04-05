import uuid
from pydantic import BaseModel
from datetime import datetime


class SyncCommand(BaseModel):
    command_id: str
    event_id: str
    event_type: str
    pms_provider: str
    hotel_id: str
    pms_property_id: str
    timestamp: datetime
    data: dict
    retry_count: int = 0
    created_at: datetime

    @classmethod
    def create(
        cls,
        event_id: str,
        event_type: str,
        pms_provider: str,
        hotel_id: str,
        pms_property_id: str,
        timestamp: datetime,
        data: dict,
    ) -> "SyncCommand":
        return cls(
            command_id=str(uuid.uuid4()),
            event_id=event_id,
            event_type=event_type,
            pms_provider=pms_provider,
            hotel_id=hotel_id,
            pms_property_id=pms_property_id,
            timestamp=timestamp,
            data=data,
            retry_count=0,
            created_at=datetime.utcnow(),
        )

    def to_json(self) -> str:
        return self.model_dump_json()
