import hashlib
import hmac
import logging
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.webhook import WebhookPayload, WebhookResponse
from app.services.webhook_facade import handle_webhook
from app.services.property_service import get_property_by_pms

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_hmac_signature(body: bytes, secret: str, signature: str) -> bool:
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/webhook", response_model=WebhookResponse, status_code=202)
async def receive_webhook(
    request: Request,
    payload: WebhookPayload,
    db: AsyncSession = Depends(get_db),
):
    role = getattr(request.state, "user_role", "")

    # If the caller is a PMS system (no JWT), validate via HMAC
    if role == "pms_system":
        pms_provider = request.headers.get("X-PMS-Provider")
        signature = request.headers.get("X-PMS-Signature")

        if not pms_provider or not signature:
            raise HTTPException(
                status_code=401,
                detail="Missing X-PMS-Provider or X-PMS-Signature headers",
            )

        # Look up the webhook secret for this PMS property
        pms_prop = await get_property_by_pms(db, pms_provider, payload.pms_property_id)
        if not pms_prop:
            raise HTTPException(status_code=404, detail="PMS property not found")

        if not pms_prop.webhook_secret_hash:
            raise HTTPException(status_code=401, detail="Webhook secret not configured")

        body = await request.body()
        if not verify_hmac_signature(body, pms_prop.webhook_secret_hash, signature):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    response = await handle_webhook(db, payload)
    return response
