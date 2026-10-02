from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app.models.models import BookingStatus

if TYPE_CHECKING:
    from app.schemas.catalogue import CentreTestResponse


class BookingCreateRequest(BaseModel):
    centre_test_id: str
    appointment_time: datetime
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("appointment_time")
    @classmethod
    def appointment_must_be_future(cls, v: datetime) -> datetime:
        """Appointment must be at least 1 hour in the future."""
        now = datetime.now(timezone.utc)
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        if v < now + timedelta(hours=1):
            raise ValueError("Appointment must be at least 1 hour in the future")
        return v


class BookingResponse(BaseModel):
    id: str
    user_id: str
    centre_test_id: str
    appointment_time: datetime
    total_amount: Decimal
    status: BookingStatus
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

