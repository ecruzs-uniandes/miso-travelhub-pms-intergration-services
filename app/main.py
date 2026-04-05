import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware

from app.database import create_tables
from app.middleware.auth_middleware import AuthMiddleware
from app.middleware.rate_limit_filter import RateLimitFilter
from app.middleware.ip_validation_filter import IPValidationFilter
from app.middleware.rbac_filter import RBACFilter
from app.api import health, webhook, properties, availability
from app.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up pms-integration-services...")
    await create_tables()
    logger.info("Database tables created/verified.")
    yield
    logger.info("Shutting down pms-integration-services...")
    from app.services.kafka_producer import close_producer
    close_producer()


app = FastAPI(
    title="PMS Integration Services",
    description="TravelHub — Webhook & sync integration for PMS providers",
    version="1.0.0",
    lifespan=lifespan,
)

# Chain of Responsibility middleware (added in reverse execution order for Starlette)
app.add_middleware(BaseHTTPMiddleware, dispatch=RBACFilter())
app.add_middleware(BaseHTTPMiddleware, dispatch=IPValidationFilter())
app.add_middleware(BaseHTTPMiddleware, dispatch=RateLimitFilter())
app.add_middleware(BaseHTTPMiddleware, dispatch=AuthMiddleware())

# Routers
app.include_router(health.router)
app.include_router(webhook.router, prefix="/api/v1/pms")
app.include_router(properties.router, prefix="/api/v1/pms")
app.include_router(availability.router, prefix="/api/v1/pms")
