from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timezone
from decimal import Decimal
from app.models.models import Payment, WebhookEvent, PaymentStatus, WebhookProcessingStatus


class PaymentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        booking_id: str,
        idempotency_key: str,
        amount: Decimal,
        transaction_reference: Optional[str] = None,
    ) -> Payment:
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=idempotency_key,
            amount=amount,
            transaction_reference=transaction_reference,
            status=PaymentStatus.INITIATED,
        )
        self.db.add(payment)
        self.db.flush()
        return payment

    def get_by_id(self, payment_id: str) -> Optional[Payment]:
        return self.db.query(Payment).filter(Payment.id == payment_id).first()

    def get_by_transaction_reference(self, txn_ref: str) -> Optional[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.transaction_reference == txn_ref)
            .first()
        )

    def get_by_booking_id(self, booking_id: str) -> Optional[Payment]:
        return (
            self.db.query(Payment)
            .filter(Payment.booking_id == booking_id)
            .order_by(Payment.created_at.desc())
            .first()
        )

    def update_status(
        self,
        payment: Payment,
        status: PaymentStatus,
        transaction_reference: Optional[str] = None,
        failure_reason: Optional[str] = None,
        provider_metadata: Optional[dict] = None,
    ) -> Payment:
        payment.status = status
        if transaction_reference:
            payment.transaction_reference = transaction_reference
        if failure_reason:
            payment.failure_reason = failure_reason
        if provider_metadata:
            payment.provider_metadata = provider_metadata
        self.db.flush()
        return payment


class WebhookEventRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_event_id(self, event_id: str) -> Optional[WebhookEvent]:
        return (
            self.db.query(WebhookEvent)
            .filter(WebhookEvent.event_id == event_id)
            .first()
        )

    def create(
        self,
        event_id: str,
        event_type: str,
        payload: dict,
        processing_status: WebhookProcessingStatus = WebhookProcessingStatus.PROCESSED,
    ) -> WebhookEvent:
        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            processing_status=processing_status,
            processed_at=datetime.now(timezone.utc),
        )
        self.db.add(event)
        self.db.flush()
        return event

    def mark_duplicate(self, event: WebhookEvent) -> WebhookEvent:
        event.processing_status = WebhookProcessingStatus.DUPLICATE_IGNORED
        self.db.flush()
        return event
