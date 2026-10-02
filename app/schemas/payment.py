from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal
from app.models.models import PaymentStatus, WebhookProcessingStatus


# ─── Simulate Payment ─────────────────────────────────────────────────────────

class PaymentSimulateRequest(BaseModel):
    booking_id: str
    force_status: Literal["SUCCESS", "FAILED", "RANDOM"] = "RANDOM"


class PaymentSimulateResponse(BaseModel):
    payment_id: str
    booking_id: str
    transaction_reference: str
    amount: Decimal
    payment_status: PaymentStatus
    booking_status: str

    model_config = {"from_attributes": True}


# ─── Webhook ──────────────────────────────────────────────────────────────────

class WebhookEventData(BaseModel):
    transaction_reference: str
    booking_id: str
    amount: Decimal
    currency: str = "INR"
    status: Literal["SUCCESS", "FAILED"]
    failure_reason: Optional[str] = None


class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=1, description="Unique identifier for the webhook event")
    event_type: str
    timestamp: datetime
    data: WebhookEventData


class WebhookResponse(BaseModel):
    status: Literal["processed", "ignored", "error"]
    message: str
    event_id: str


# ─── Payment Detail ───────────────────────────────────────────────────────────

class PaymentResponse(BaseModel):
    id: str
    booking_id: str
    transaction_reference: Optional[str]
    amount: Decimal
    status: PaymentStatus
    failure_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
