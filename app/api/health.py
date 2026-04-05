import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.schemas.common import HealthResponse
from app.config import settings
from app.services.kafka_producer import get_producer

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: AsyncSession = Depends(get_db)):
    # Check DB
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"DB health check failed: {e}")
        db_status = "error"

    # Check Kafka
    kafka_status = "disabled"
    if settings.KAFKA_ENABLED:
        producer = get_producer()
        kafka_status = "ok" if producer is not None else "error"

    return HealthResponse(
        status="ok" if db_status == "ok" else "degraded",
        service=settings.SERVICE_NAME,
        database=db_status,
        kafka=kafka_status,
    )
