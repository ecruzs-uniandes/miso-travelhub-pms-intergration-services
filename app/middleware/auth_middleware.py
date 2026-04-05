import logging
from typing import Optional
from fastapi import Request, HTTPException
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# Routes accessible without JWT (PMS webhook uses HMAC or is pre-validated by gateway)
WEBHOOK_PATH = "/api/v1/pms/webhook"


def decode_jwt_no_verify(token: str) -> dict:
    """Decode JWT without signature verification (API Gateway already verified it)."""
    try:
        payload = jwt.decode(
            token,
            key="",
            algorithms=["HS256", "RS256"],
            options={"verify_signature": False, "verify_exp": False},
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise HTTPException(status_code=401, detail="Invalid token")


def extract_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
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
        # Webhook path supports HMAC auth — skip JWT requirement
        if request.url.path == WEBHOOK_PATH:
            token = extract_token(request)
            if token:
                try:
                    payload = decode_jwt_no_verify(token)
                    set_user_context(request, payload)
                except HTTPException:
                    pass  # Will be validated by webhook handler via HMAC
            request.state.user_id = getattr(request.state, "user_id", None)
            request.state.user_role = getattr(request.state, "user_role", "pms_system")
            return await call_next(request)

        # All other routes require a valid JWT
        token = extract_token(request)
        if not token:
            raise HTTPException(status_code=401, detail="Missing authentication token")

        payload = decode_jwt_no_verify(token)
        set_user_context(request, payload)
        return await call_next(request)
