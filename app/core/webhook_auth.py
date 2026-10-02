"""
HMAC-SHA256 webhook signature verification.
The payment gateway signs the raw request body using a shared secret.
We verify the signature to prevent spoofed webhook events.
"""
import hashlib
import hmac
import logging
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)

SIGNATURE_HEADER = "X-Eve-Signature"


def compute_hmac_signature(body: bytes, secret: str) -> str:
    """Compute HMAC-SHA256 of body bytes using the shared secret."""
    return hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()


async def verify_webhook_signature(request: Request) -> None:
    """
    FastAPI dependency: verifies the X-Eve-Signature header.
    Skipped when ENABLE_WEBHOOK_HMAC=False (local development).

    Attack scenario this prevents:
    - Malicious actor sends a crafted webhook to mark payments as SUCCESS
      without the HMAC secret they cannot produce a valid signature.
    """
    if not settings.ENABLE_WEBHOOK_HMAC:
        return  # Disabled in dev/test environments

    signature = request.headers.get(SIGNATURE_HEADER)
    if not signature:
        logger.warning("Webhook received without signature header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Missing required header: {SIGNATURE_HEADER}",
        )

    body = await request.body()
    expected = compute_hmac_signature(body, settings.WEBHOOK_SECRET_KEY)

    if not hmac.compare_digest(signature, expected):
        logger.warning("Webhook signature mismatch — possible spoofing attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    logger.info("Webhook signature verified successfully")
