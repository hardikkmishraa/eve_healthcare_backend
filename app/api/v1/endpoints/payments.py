from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user_id
from app.core.cache import limiter
from app.core.webhook_auth import verify_webhook_signature
from app.core.config import settings
from app.services.payment_service import PaymentService
from app.schemas.payment import (
    PaymentSimulateRequest, PaymentSimulateResponse,
    WebhookPayload, WebhookResponse,
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "",
    response_model=PaymentSimulateResponse,
    summary="Simulate a payment for a booking",
    description="Rate limited to 20 requests/minute per IP.",
)
@router.post(
    "/",
    response_model=PaymentSimulateResponse,
    include_in_schema=False,
)
@router.post(
    "/simulate",
    response_model=PaymentSimulateResponse,
    include_in_schema=False,
)
@limiter.limit(settings.RATE_LIMIT_PAYMENT)
def simulate_payment(
    request: Request,  # Required by SlowAPI for rate limiting
    body: PaymentSimulateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Simulate payment processing for a booking.

    **Force Status Options:**
    - `SUCCESS` — Always succeeds
    - `FAILED` — Always fails
    - `RANDOM` — Probabilistic (configurable PAYMENT_SUCCESS_RATE, default 80%)

    Only the booking owner can initiate payment. Booking must be **PENDING**.

    On success → booking moves to **CONFIRMED** + background notification dispatched.
    On failure → booking moves to **FAILED** + background notification dispatched.

    **Rate limit:** 20 requests/minute per IP.
    """
    service = PaymentService(db)
    return service.simulate_payment(body, user_id)


@router.post(
    "/webhook",
    response_model=WebhookResponse,
    summary="Receive payment status webhook (idempotent, HMAC-verified)",
)
async def payment_webhook(
    request: Request,
    payload: WebhookPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_webhook_signature),  # HMAC verification (optional in dev)
):
    """
    Receive a payment status update from the (simulated) payment gateway.

    **Idempotency Guarantees:**
    - Duplicate events (same `event_id`) are safely ignored with HTTP 200.
    - Row-level database locking prevents race conditions with concurrent deliveries.
    - Settled bookings (CONFIRMED/FAILED/CANCELLED) cannot be regressed.

    **Security (Production):**
    - When `ENABLE_WEBHOOK_HMAC=true`, requires `X-Eve-Signature: <hmac-sha256-hex>` header.
    - Signature is computed as `HMAC-SHA256(request_body, WEBHOOK_SECRET_KEY)`.

    **Expected Payload:**
    ```json
    {
      "event_id": "evt_unique_123",
      "event_type": "payment.updated",
      "timestamp": "2026-10-01T12:00:00Z",
      "data": {
        "transaction_reference": "txn_mock_ABCDEF123456",
        "booking_id": "...",
        "amount": 1499.00,
        "currency": "INR",
        "status": "SUCCESS",
        "failure_reason": null
      }
    }
    ```
    """
    service = PaymentService(db)
    return service.process_webhook(payload)
