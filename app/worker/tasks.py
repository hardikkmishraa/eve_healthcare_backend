"""
Celery application and background task definitions.

Tasks:
1. send_booking_notification  — Simulate email/SMS notification on booking status change
2. auto_cancel_stale_bookings — Scan and cancel PENDING bookings stuck past timeout window
"""
import logging
from datetime import datetime, timedelta, timezone
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

logger = logging.getLogger(__name__)

# ─── Celery App ───────────────────────────────────────────────────────────────

celery_app = Celery(
    "eve_healthcare",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,  # Only ack after task completes (safe for at-least-once delivery)
    # Beat schedule for periodic tasks
    beat_schedule={
        "auto-cancel-stale-bookings": {
            "task": "app.worker.tasks.auto_cancel_stale_bookings",
            "schedule": crontab(minute="*/5"),  # Every 5 minutes
        }
    },
)


# ─── Task Definitions ─────────────────────────────────────────────────────────

@celery_app.task(
    name="app.worker.tasks.send_booking_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # seconds
    autoretry_for=(Exception,),
)
def send_booking_notification(self, booking_id: str, user_email: str, user_name: str,
                               booking_status: str, amount: float, appointment_time: str) -> dict:
    """
    Simulate sending an email/SMS notification when a booking status changes.

    In production this would:
    - Trigger an email via SendGrid/SES
    - Send an SMS via Twilio/AWS SNS
    - Push an in-app notification

    Args:
        booking_id: The booking UUID
        user_email: Recipient email address
        user_name: Patient's full name
        booking_status: New booking status (CONFIRMED, FAILED, CANCELLED)
        amount: Booking amount in INR
        appointment_time: ISO 8601 appointment datetime string
    """
    try:
        # Simulate notification dispatch (replace with real provider in production)
        message_map = {
            "CONFIRMED": (
                f"✅ Your booking #{booking_id[:8]} is CONFIRMED! "
                f"Appointment on {appointment_time}. Amount paid: ₹{amount:.2f}"
            ),
            "FAILED": (
                f"❌ Your booking #{booking_id[:8]} could not be confirmed due to payment failure. "
                f"Please try booking again."
            ),
            "CANCELLED": (
                f"🔔 Your booking #{booking_id[:8]} has been CANCELLED. "
                f"Contact support if this was unexpected."
            ),
        }
        message = message_map.get(booking_status, f"Your booking status has been updated to {booking_status}.")

        # Simulate I/O (real sending would happen here)
        logger.info(
            "Notification dispatched",
            extra={
                "task": "send_booking_notification",
                "booking_id": booking_id,
                "recipient": user_email,
                "status": booking_status,
                "message_preview": message[:80],
            }
        )

        return {
            "status": "sent",
            "channel": "email+sms",
            "recipient": user_email,
            "booking_id": booking_id,
            "notification_type": booking_status,
            "message": message,
        }

    except Exception as exc:
        retries = getattr(self.request, "retries", 0) if hasattr(self, "request") else 0
        logger.error(
            "Notification dispatch failed — retrying",
            extra={"booking_id": booking_id, "error": str(exc), "retry": retries}
        )
        if hasattr(self, "retry"):
            raise self.retry(exc=exc)
        raise exc


@celery_app.task(
    name="app.worker.tasks.auto_cancel_stale_bookings",
)
def auto_cancel_stale_bookings() -> dict:
    """
    Periodic task: find PENDING bookings older than PENDING_BOOKING_TIMEOUT_MINUTES
    and automatically cancel them to free inventory.

    Runs every 5 minutes via Celery Beat.
    """
    from app.db.session import SessionLocal
    from app.models.models import Booking, BookingStatus

    db = SessionLocal()
    cancelled_count = 0
    try:
        cutoff_time = datetime.now(timezone.utc) - timedelta(
            minutes=settings.PENDING_BOOKING_TIMEOUT_MINUTES
        )

        query = db.query(Booking).filter(
            Booking.status == BookingStatus.PENDING,
            Booking.created_at < cutoff_time,
        )
        # PostgreSQL supports SKIP LOCKED for concurrent safe worker execution
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update(skip_locked=True)

        stale_bookings = query.all()

        for booking in stale_bookings:
            booking.status = BookingStatus.CANCELLED
            cancelled_count += 1
            logger.info(
                "Stale booking auto-cancelled",
                extra={
                    "task": "auto_cancel_stale_bookings",
                    "booking_id": booking.id,
                    "age_minutes": settings.PENDING_BOOKING_TIMEOUT_MINUTES,
                }
            )

        db.commit()

        logger.info(
            "Stale booking cleanup complete",
            extra={"task": "auto_cancel_stale_bookings", "cancelled_count": cancelled_count}
        )
        return {"cancelled_count": cancelled_count, "cutoff_time": cutoff_time.isoformat()}

    except Exception as exc:
        db.rollback()
        logger.error("Stale booking cleanup failed", extra={"error": str(exc)})
        raise
    finally:
        db.close()
