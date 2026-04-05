import logging
from fastapi import Request

logger = logging.getLogger(__name__)


class IPValidationFilter:
    """
    Chain of Responsibility — Step 3.
    Placeholder for geolocation / IP allowlist validation.
    """

    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        logger.debug(f"Request from IP: {client_ip}")
        # Future: implement geo-blocking or allowlist
        return await call_next(request)
