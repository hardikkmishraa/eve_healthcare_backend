import uuid
import random
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


from app.core.config import settings
from app.repositories.booking_repository import BookingRepository
from app.repositories.payment_repository import PaymentRepository, WebhookEventRepository
from app.models.models import (
    Booking, BookingStatus, Payment, PaymentStatus, WebhookProcessingStatus
)
from app.schemas.payment import PaymentSimulateRequest, PaymentSimulateResponse, WebhookPayload, WebhookResponse


class PaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.payment_repo = PaymentRepository(db)
        self.webhook_repo = WebhookEventRepository(db)

    def simulate_payment(
        self, request: PaymentSimulateRequest, requesting_user_id: str
    ) -> PaymentSimulateResponse:
        """
        Simulate a payment for a booking.
        - Only the booking owner can initiate payment.
        - Booking must be in PENDING state.
        - Outcome determined by force_status or random probability.
        """
        booking = self.booking_repo.get_by_id(request.booking_id)
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking '{request.booking_id}' not found",
            )
        # Ownership check
        if booking.user_id != requesting_user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found",  # 404, not 403, to prevent ID enumeration
            )
        # Booking must be PENDING to initiate payment
        if booking.status != BookingStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot initiate payment for a booking in '{booking.status.value}' state. "
                       f"Payment can only be initiated for PENDING bookings.",
            )

        # Determine payment outcome
        if request.force_status == "SUCCESS":
            succeed = True
        elif request.force_status == "FAILED":
            succeed = False
        else:  # RANDOM
            succeed = random.random() < settings.PAYMENT_SUCCESS_RATE

        idempotency_key = str(uuid.uuid4())
        txn_ref = f"txn_mock_{uuid.uuid4().hex[:12].upper()}"
        failure_reason = None if succeed else "Simulated payment decline - insufficient funds"

        # Create the payment record
        payment = self.payment_repo.create(
            booking_id=booking.id,
            idempotency_key=idempotency_key,
            amount=booking.total_amount,
            transaction_reference=txn_ref,
        )

        # Update payment and booking status atomically
        payment_status = PaymentStatus.SUCCESS if succeed else PaymentStatus.FAILED
        booking_status = BookingStatus.CONFIRMED if succeed else BookingStatus.FAILED

        self.payment_repo.update_status(
            payment,
            status=payment_status,
            failure_reason=failure_reason,
            provider_metadata={
                "simulated": True,
                "force_status": request.force_status,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        self.booking_repo.update_status(booking, booking_status)
        self.db.commit()

        logger.info(
            "Payment simulation complete",
            extra={
                "booking_id": booking.id,
                "payment_id": payment.id,
                "payment_status": payment_status.value,
                "booking_status": booking_status.value,
                "txn_ref": txn_ref,
            }
        )

        # Dispatch async notification (fire-and-forget via Celery)
        try:
            from app.worker.tasks import send_booking_notification
            from app.repositories.user_repository import UserRepository
            user = UserRepository(self.db).get_by_id(booking.user_id)
            if user:
                send_booking_notification.delay(
                    booking_id=booking.id,
                    user_email=user.email,
                    user_name=user.full_name,
                    booking_status=booking_status.value,
                    amount=float(booking.total_amount),
                    appointment_time=str(booking.appointment_time),
                )
        except Exception as notify_err:
            # Notification failure must NEVER block the payment response
            logger.warning("Could not dispatch notification", extra={"error": str(notify_err)})

        return PaymentSimulateResponse(
            payment_id=payment.id,
            booking_id=booking.id,
            transaction_reference=txn_ref,
            amount=payment.amount,
            payment_status=payment_status,
            booking_status=booking_status.value,
        )

    def process_webhook(self, payload: WebhookPayload) -> WebhookResponse:
        """
        Idempotent webhook processor.

        Idempotency strategy:
        1. Check if event_id already exists in webhook_events table.
           If yes: return 200 with 'ignored' status immediately (no duplicate processing).
        2. Lock the booking row (SELECT FOR UPDATE) before any state change.
        3. Validate state transition; if booking already settled, log as DUPLICATE_IGNORED.
        4. Apply payment and booking status updates atomically.
        5. Record the webhook event in the deduplication store.

        This handles:
        - Exact duplicate deliveries (same event_id)
        - Network retry storms
        - Concurrent deliveries of the same event
        - Out-of-order / late delivery after booking already settled
        """
        raw_payload = payload.model_dump(mode="json")

        # ── Step 1: Check deduplication store ──────────────────────────────
        existing_event = self.webhook_repo.get_by_event_id(payload.event_id)
        if existing_event:
            return WebhookResponse(
                status="ignored",
                message=f"Duplicate event '{payload.event_id}' already processed — ignored",
                event_id=payload.event_id,
            )

        # ── Step 2: Find payment by transaction_reference ──────────────────
        data = payload.data
        payment = self.payment_repo.get_by_transaction_reference(data.transaction_reference)
        if not payment:
            # Record failed event before raising
            self.webhook_repo.create(
                event_id=payload.event_id,
                event_type=payload.event_type,
                payload=raw_payload,
                processing_status=WebhookProcessingStatus.FAILED,
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No payment found with transaction_reference '{data.transaction_reference}'",
            )

        # ── Step 3: Acquire row-level lock on booking ──────────────────────
        booking = self.booking_repo.get_by_id_for_update(data.booking_id)
        if not booking:
            self.webhook_repo.create(
                event_id=payload.event_id,
                event_type=payload.event_type,
                payload=raw_payload,
                processing_status=WebhookProcessingStatus.FAILED,
            )
            self.db.commit()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking '{data.booking_id}' not found",
            )

        # ── Step 4: Validate state transition ─────────────────────────────
        target_booking_status = (
            BookingStatus.CONFIRMED if data.status == "SUCCESS" else BookingStatus.FAILED
        )
        target_payment_status = (
            PaymentStatus.SUCCESS if data.status == "SUCCESS" else PaymentStatus.FAILED
        )

        if not self.booking_repo.can_transition(booking, target_booking_status):
            # Booking already settled — log as DUPLICATE_IGNORED, return 200
            try:
                self.webhook_repo.create(
                    event_id=payload.event_id,
                    event_type=payload.event_type,
                    payload=raw_payload,
                    processing_status=WebhookProcessingStatus.DUPLICATE_IGNORED,
                )
                self.db.commit()
            except IntegrityError:
                self.db.rollback()
            return WebhookResponse(
                status="ignored",
                message=(
                    f"Booking '{booking.id}' is already in '{booking.status.value}' state. "
                    f"Attempted transition to '{target_booking_status.value}' is disallowed."
                ),
                event_id=payload.event_id,
            )

        # ── Step 5: Apply updates atomically ──────────────────────────────
        self.payment_repo.update_status(
            payment,
            status=target_payment_status,
            failure_reason=data.failure_reason,
            provider_metadata={"webhook_event_id": payload.event_id},
        )
        self.booking_repo.update_status(booking, target_booking_status)

        # ── Step 6: Record successful event processing ─────────────────────
        try:
            self.webhook_repo.create(
                event_id=payload.event_id,
                event_type=payload.event_type,
                payload=raw_payload,
                processing_status=WebhookProcessingStatus.PROCESSED,
            )
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            return WebhookResponse(
                status="ignored",
                message=f"Duplicate event '{payload.event_id}' already processed — ignored",
                event_id=payload.event_id,
            )

        return WebhookResponse(
            status="processed",
            message=f"Booking '{booking.id}' updated to '{target_booking_status.value}'",
            event_id=payload.event_id,
        )
