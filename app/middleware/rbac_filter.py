import logging
from fastapi import Request, HTTPException

logger = logging.getLogger(__name__)

# RBAC rules
# hotel_admin and platform_admin can access all /api/v1/pms/* routes
# traveler can only GET /api/v1/pms/availability
# pms_system is set when webhook comes via HMAC (no JWT role)
WEBHOOK_PATH = "/api/v1/pms/webhook"
AVAILABILITY_PATH = "/api/v1/pms/availability"

ADMIN_ROLES = {"hotel_admin", "platform_admin"}
TRAVELER_ROLE = "traveler"
PMS_SYSTEM_ROLE = "pms_system"


class RBACFilter:
    """
    Chain of Responsibility — Step 4.
    Validates that the authenticated role is allowed on the requested path/method.
    """

    async def __call__(self, request: Request, call_next):
        path = request.url.path
        method = request.method
        role = getattr(request.state, "user_role", "")

        # Health endpoint is always open
        if path == "/health":
            return await call_next(request)

        # Webhook: allow pms_system (HMAC auth) or hotel_admin/platform_admin
        if path == WEBHOOK_PATH and method == "POST":
            if role in ADMIN_ROLES or role == PMS_SYSTEM_ROLE:
                return await call_next(request)
            raise HTTPException(status_code=403, detail="Forbidden")

        # Traveler: only GET availability
        if role == TRAVELER_ROLE:
            if path.startswith(AVAILABILITY_PATH) and method == "GET":
                return await call_next(request)
            raise HTTPException(status_code=403, detail="Forbidden")

        # Admin roles: all PMS routes
        if role in ADMIN_ROLES:
            return await call_next(request)

        raise HTTPException(status_code=403, detail="Forbidden")
