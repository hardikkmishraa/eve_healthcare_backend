import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Numeric, ForeignKey,
    Enum as SAEnum, Text, UniqueConstraint, CheckConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ─── Enums ───────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    ADMIN = "ADMIN"


class BookingStatus(str, enum.Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PaymentStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class WebhookProcessingStatus(str, enum.Enum):
    PROCESSED = "PROCESSED"
    DUPLICATE_IGNORED = "DUPLICATE_IGNORED"
    FAILED = "FAILED"


# ─── Models ──────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone_number = Column(String(20), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False, default=UserRole.PATIENT)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    bookings = relationship("Booking", back_populates="user", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class DiagnosticCentre(Base):
    __tablename__ = "diagnostic_centres"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False, index=True)
    pincode = Column(String(10), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    centre_tests = relationship("CentreTest", back_populates="centre", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DiagnosticCentre id={self.id} name={self.name}>"


class DiagnosticTest(Base):
    __tablename__ = "diagnostic_tests"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    sample_type = Column(String(100), nullable=True)  # e.g., Blood, Urine, Imaging
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    centre_tests = relationship("CentreTest", back_populates="test", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<DiagnosticTest id={self.id} name={self.name}>"


class CentreTest(Base):
    """Join table associating centres with their offered tests + localized pricing."""
    __tablename__ = "centre_tests"

    __table_args__ = (
        UniqueConstraint("centre_id", "test_id", name="uq_centre_test"),
        CheckConstraint("price > 0", name="ck_centre_test_price_positive"),
    )

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    centre_id = Column(UUID(as_uuid=False), ForeignKey("diagnostic_centres.id", ondelete="RESTRICT"), nullable=False)
    test_id = Column(UUID(as_uuid=False), ForeignKey("diagnostic_tests.id", ondelete="RESTRICT"), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    is_available = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    centre = relationship("DiagnosticCentre", back_populates="centre_tests")
    test = relationship("DiagnosticTest", back_populates="centre_tests")
    bookings = relationship("Booking", back_populates="centre_test", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<CentreTest centre={self.centre_id} test={self.test_id} price={self.price}>"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    centre_test_id = Column(UUID(as_uuid=False), ForeignKey("centre_tests.id", ondelete="RESTRICT"), nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    total_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SAEnum(BookingStatus), nullable=False, default=BookingStatus.PENDING, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="bookings")
    centre_test = relationship("CentreTest", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Booking id={self.id} status={self.status}>"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    booking_id = Column(UUID(as_uuid=False), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False, index=True)
    idempotency_key = Column(String(255), nullable=False, unique=True, index=True)
    transaction_reference = Column(String(255), nullable=True, unique=True, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(SAEnum(PaymentStatus), nullable=False, default=PaymentStatus.INITIATED)
    failure_reason = Column(Text, nullable=True)
    provider_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    booking = relationship("Booking", back_populates="payments")

    def __repr__(self) -> str:
        return f"<Payment id={self.id} status={self.status}>"


class WebhookEvent(Base):
    """Deduplication store for incoming payment webhook events."""
    __tablename__ = "webhook_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=generate_uuid)
    event_id = Column(String(255), nullable=False, unique=True, index=True)
    event_type = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False)
    processing_status = Column(
        SAEnum(WebhookProcessingStatus),
        nullable=False,
        default=WebhookProcessingStatus.PROCESSED,
    )
    received_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<WebhookEvent event_id={self.event_id} status={self.processing_status}>"
