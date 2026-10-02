from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.security import get_current_user_id
from app.services.booking_service import BookingService
from app.services.auth_service import AuthService
from app.schemas.booking import BookingCreateRequest, BookingResponse
from app.models.models import UserRole

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new booking",
)
def create_booking(
    request: BookingCreateRequest,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Book a diagnostic test at a specific centre.

    - **centre_test_id**: The ID of the centre-test listing (from `GET /centres/{id}/tests`)
    - **appointment_time**: Must be at least 1 hour in the future (ISO 8601 datetime)
    - **notes**: Optional patient notes

    The booking amount is determined server-side from the centre's listed price.
    **Never trust client-provided pricing.**
    """
    service = BookingService(db)
    return service.create_booking(user_id, request)


@router.get(
    "/my",
    response_model=dict,
    summary="List my bookings",
)
def list_my_bookings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """List all bookings made by the currently authenticated user, newest first."""
    service = BookingService(db)
    return service.list_my_bookings(user_id, page=page, page_size=page_size)


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    summary="Get booking detail",
)
def get_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Retrieve a specific booking by ID.

    - Patients can only view their own bookings.
    - Returns 404 for bookings that belong to other users (prevents ID enumeration).
    """
    auth_service = AuthService(db)
    user = auth_service.get_current_user(user_id)
    service = BookingService(db)
    return service.get_booking(booking_id, user_id, user.role)


@router.post(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    summary="Cancel a booking",
)
def cancel_booking(
    booking_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """
    Cancel a booking.

    - Only **PENDING** or **CONFIRMED** bookings can be cancelled.
    - **FAILED** and **CANCELLED** are terminal states and cannot be modified.
    - Returns 409 Conflict if the current state disallows cancellation.
    """
    auth_service = AuthService(db)
    user = auth_service.get_current_user(user_id)
    service = BookingService(db)
    return service.cancel_booking(booking_id, user_id, user.role)
