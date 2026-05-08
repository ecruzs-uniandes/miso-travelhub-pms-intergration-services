import logging
from typing import Optional
from fastapi import Request
from starlette.responses import JSONResponse
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# Routes accessible without JWT (PMS webhook uses HMAC or is pre-validated by gateway)
WEBHOOK_PATH = "/api/v1/pms/webhook"

# Public routes (health checks, docs) — no JWT required
PUBLIC_PATHS = {"/health", "/docs", "/redoc", "/openapi.json"}


def decode_jwt_no_verify(token: str) -> dict:
    """Decode JWT without signature verification (API Gateway already verified it)."""
    try:
        payload = jwt.decode(
            token,
            key="",
            algorithms=["HS256", "RS256"],
            options={"verify_signature": False, "verify_exp": False, "verify_aud": False},
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        return None


def extract_token(request: Request) -> Optional[str]:
    # When traffic comes through API Gateway, GCP replaces "Authorization" with a
    # service OIDC token and moves the original user JWT to "X-Forwarded-Authorization".
    # Read X-Forwarded-Authorization first; fall back to Authorization for direct calls.
    for header in ("X-Forwarded-Authorization", "Authorization"):
        value = request.headers.get(header, "")
        if value.startswith("Bearer "):
            return value[7:]
    return None


def set_user_context(request: Request, payload: dict) -> None:
    request.state.user_id = payload.get("sub")
    request.state.user_role = payload.get("role", "")
    request.state.user_email = payload.get("email", "")


class AuthMiddleware:
    """
    Chain of Responsibility — Step 1.
    Decodes JWT from Authorization header and sets request.state.user_*.
    If no JWT and path is NOT the webhook, blocks with 401.
    """

    async def __call__(self, request: Request, call_next):
        path = request.url.path

        # Public routes (health, docs) bypass auth entirely
        if path in PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            request.state.user_id = None
            request.state.user_role = "public"
            return await call_next(request)

        # Webhook path supports HMAC auth — skip JWT requirement
        if path == WEBHOOK_PATH:
            token = extract_token(request)
            if token:
                payload = decode_jwt_no_verify(token)
                if payload:
                    set_user_context(request, payload)
            request.state.user_id = getattr(request.state, "user_id", None)
            request.state.user_role = getattr(request.state, "user_role", "pms_system")
            return await call_next(request)

        # All other routes require a valid JWT
        token = extract_token(request)
        if not token:
            return JSONResponse(status_code=401, content={"detail": "Missing authentication token"})

        payload = decode_jwt_no_verify(token)
        if payload is None:
            return JSONResponse(status_code=401, content={"detail": "Invalid token"})
        set_user_context(request, payload)
        return await call_next(request)
