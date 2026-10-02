from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, List

from app.repositories.booking_repository import BookingRepository
from app.repositories.catalogue_repository import CatalogueRepository
from app.models.models import Booking, BookingStatus, UserRole
from app.schemas.booking import BookingCreateRequest, BookingResponse


class BookingService:
    def __init__(self, db: Session):
        self.db = db
        self.booking_repo = BookingRepository(db)
        self.catalogue_repo = CatalogueRepository(db)

    def create_booking(self, user_id: str, request: BookingCreateRequest) -> Booking:
        """
        Create a booking.
        - Validates that the centre-test exists and is available.
        - Server-side price lookup: the total_amount is never trusted from the client.
        - Booking starts in PENDING status.
        """
        ct = self.catalogue_repo.get_centre_test_by_id(request.centre_test_id)
        if not ct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Centre-test listing '{request.centre_test_id}' not found",
            )
        if not ct.is_available:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This diagnostic test is currently unavailable at the selected centre",
            )
        if not ct.centre.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The selected diagnostic centre is currently inactive",
            )
        # Server-side price: never trust client-provided amount
        booking = self.booking_repo.create(
            user_id=user_id,
            centre_test_id=request.centre_test_id,
            appointment_time=request.appointment_time,
            total_amount=ct.price,  # authoritative price from DB
            notes=request.notes,
        )
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def get_booking(self, booking_id: str, user_id: str, user_role: UserRole) -> Booking:
        """
        Fetch booking detail.
        - Patients can only view their own bookings.
        - Admins can view any booking.
        - Returns 404 (not 403) for unauthorized access to prevent ID enumeration.
        """
        booking = self.booking_repo.get_by_id(booking_id)
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Booking not found")
        if user_role != UserRole.ADMIN and booking.user_id != user_id:
            # Return 404 to avoid leaking existence of other users' bookings
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Booking not found")
        return booking

    def list_my_bookings(self, user_id: str, page: int = 1, page_size: int = 20) -> dict:
        skip = (page - 1) * page_size
        results, total = self.booking_repo.get_user_bookings(user_id, skip=skip, limit=page_size)
        # Serialize ORM objects to dicts for JSON-safe dict response
        serialized = [BookingResponse.model_validate(b).model_dump() for b in results]
        return {"total": total, "page": page, "page_size": page_size, "results": serialized}

    def cancel_booking(self, booking_id: str, user_id: str, user_role: UserRole) -> Booking:
        """
        Cancel a booking.
        - Only PENDING or CONFIRMED bookings can be cancelled.
        - FAILED and CANCELLED are terminal states.
        - Ownership enforced (Patients can only cancel their own bookings).
        """
        booking = self.get_booking(booking_id, user_id, user_role)
        if not self.booking_repo.can_transition(booking, BookingStatus.CANCELLED):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel a booking in '{booking.status.value}' state. "
                       f"Only PENDING or CONFIRMED bookings can be cancelled.",
            )
        self.booking_repo.update_status(booking, BookingStatus.CANCELLED)
        self.db.commit()
        self.db.refresh(booking)
        return booking
