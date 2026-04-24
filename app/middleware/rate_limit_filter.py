import time
import logging
from collections import defaultdict
from fastapi import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# In-memory rate limit store: {key: [timestamp, ...]}
_request_log: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 60  # requests
WINDOW = 60  # seconds


class RateLimitFilter:
    """
    Chain of Responsibility — Step 2.
    Allows max 60 req/min per user_id or IP.
    """

    async def __call__(self, request: Request, call_next):
        user_id = getattr(request.state, "user_id", None)
        key = user_id if user_id else request.client.host if request.client else "unknown"

        now = time.time()
        window_start = now - WINDOW

        # Purge old entries
        _request_log[key] = [t for t in _request_log[key] if t > window_start]

        if len(_request_log[key]) >= RATE_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

        _request_log[key].append(now)
        return await call_next(request)
