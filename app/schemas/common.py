from pydantic import BaseModel
from typing import Optional


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    kafka: str


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
