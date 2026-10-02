from sqlalchemy.orm import Session, joinedload
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.models.models import Booking, BookingStatus, CentreTest


class BookingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: str,
        centre_test_id: str,
        appointment_time: datetime,
        total_amount: Decimal,
        notes: Optional[str] = None,
    ) -> Booking:
        booking = Booking(
            user_id=user_id,
            centre_test_id=centre_test_id,
            appointment_time=appointment_time,
            total_amount=total_amount,
            notes=notes,
            status=BookingStatus.PENDING,
        )
        self.db.add(booking)
        self.db.flush()
        return booking

    def get_by_id(self, booking_id: str) -> Optional[Booking]:
        return (
            self.db.query(Booking)
            .options(
                joinedload(Booking.centre_test)
                .joinedload(CentreTest.test),
                joinedload(Booking.centre_test)
                .joinedload(CentreTest.centre),
            )
            .filter(Booking.id == booking_id)
            .first()
        )

    def get_by_id_for_update(self, booking_id: str) -> Optional[Booking]:
        """Acquire row-level lock for atomic status updates (webhook idempotency)."""
        return (
            self.db.query(Booking)
            .filter(Booking.id == booking_id)
            .with_for_update()
            .first()
        )

    def get_user_bookings(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[List[Booking], int]:
        query = (
            self.db.query(Booking)
            .filter(Booking.user_id == user_id)
            .order_by(Booking.created_at.desc())
        )
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return results, total

    def update_status(self, booking: Booking, new_status: BookingStatus) -> Booking:
        booking.status = new_status
        self.db.flush()
        return booking

    # Allowed transitions matrix
    ALLOWED_TRANSITIONS = {
        BookingStatus.PENDING: {
            BookingStatus.CONFIRMED,
            BookingStatus.FAILED,
            BookingStatus.CANCELLED,
        },
        BookingStatus.CONFIRMED: {BookingStatus.CANCELLED},
        BookingStatus.FAILED: set(),      # terminal
        BookingStatus.CANCELLED: set(),   # terminal
    }

    def can_transition(self, booking: Booking, target: BookingStatus) -> bool:
        return target in self.ALLOWED_TRANSITIONS.get(booking.status, set())
