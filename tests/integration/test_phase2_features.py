"""
Integration tests for Phase 2 production & bonus features:
- Health and Readiness Probes (/health, /ready)
- Rate Limiting Enforcement
- HMAC Webhook Signature Verification
- Celery Background Notification and Stale Booking Cleanup Tasks
- Redis Cache Key Generators & Cache Invalidation
"""
import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from decimal import Decimal

from app.core.config import settings
from app.core.cache import (
    limiter,
    make_centres_cache_key,
    make_tests_cache_key,
    make_centre_tests_cache_key,
    invalidate_centre_cache,
    cache_get,
    cache_set,
    cache_delete,
)
from app.core.webhook_auth import compute_hmac_signature, SIGNATURE_HEADER
from app.worker.tasks import send_booking_notification, auto_cancel_stale_bookings
from app.models.models import Booking, BookingStatus, Payment, PaymentStatus


class TestHealthAndReadinessProbes:
    """Tests for Kubernetes/Docker health and readiness endpoints."""

    def test_health_probe(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "service" in data
        assert "environment" in data

    def test_readiness_probe_structure(self, client):
        response = client.get("/ready")
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "checks" in data
        assert "postgres" in data["checks"]
        assert "redis" in data["checks"]

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"
        assert data["ready"] == "/ready"


class TestRateLimiter:
    """Tests for SlowAPI rate limiting behavior."""

    def test_rate_limiter_exceeded_when_enabled(self, client, test_user):
        try:
            limiter.enabled = True
            responses = []
            for _ in range(7):
                res = client.post("/api/v1/auth/login", json={
                    "email": test_user.email,
                    "password": "WrongPassword123",
                })
                responses.append(res.status_code)

            # At least one request should have hit the 429 rate limit
            assert 429 in responses
        finally:
            limiter.enabled = False  # Always reset for subsequent tests


class TestWebhookHMACVerification:
    """Tests for HMAC-SHA256 signature verification on /api/v1/payments/webhook."""

    def test_hmac_missing_header_when_enabled(self, client, db, test_user, test_centre_test):
        booking = Booking(
            user_id=test_user.id,
            centre_test_id=test_centre_test.id,
            appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
            total_amount=test_centre_test.price,
            status=BookingStatus.PENDING,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        payment = Payment(
            booking_id=booking.id,
            idempotency_key=str(uuid.uuid4()),
            transaction_reference=f"txn_{uuid.uuid4().hex[:12]}",
            amount=booking.total_amount,
            status=PaymentStatus.INITIATED,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        with patch.object(settings, "ENABLE_WEBHOOK_HMAC", True):
            payload = {
                "event_id": f"evt_{uuid.uuid4().hex}",
                "event_type": "payment.succeeded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "transaction_reference": payment.transaction_reference,
                    "booking_id": str(booking.id),
                    "amount": float(booking.total_amount),
                    "status": "SUCCESS",
                },
            }
            response = client.post("/api/v1/payments/webhook", json=payload)
            assert response.status_code == 401
            assert "Missing required header" in response.json()["detail"]

    def test_hmac_invalid_signature_when_enabled(self, client, db, test_user, test_centre_test):
        booking = Booking(
            user_id=test_user.id,
            centre_test_id=test_centre_test.id,
            appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
            total_amount=test_centre_test.price,
            status=BookingStatus.PENDING,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        payment = Payment(
            booking_id=booking.id,
            idempotency_key=str(uuid.uuid4()),
            transaction_reference=f"txn_{uuid.uuid4().hex[:12]}",
            amount=booking.total_amount,
            status=PaymentStatus.INITIATED,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        with patch.object(settings, "ENABLE_WEBHOOK_HMAC", True):
            payload = {
                "event_id": f"evt_{uuid.uuid4().hex}",
                "event_type": "payment.succeeded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "transaction_reference": payment.transaction_reference,
                    "booking_id": str(booking.id),
                    "amount": float(booking.total_amount),
                    "status": "SUCCESS",
                },
            }
            headers = {SIGNATURE_HEADER: "invalid_hex_signature_here"}
            response = client.post("/api/v1/payments/webhook", json=payload, headers=headers)
            assert response.status_code == 401
            assert "Invalid webhook signature" in response.json()["detail"]

    def test_hmac_valid_signature_success(self, client, db, test_user, test_centre_test):
        booking = Booking(
            user_id=test_user.id,
            centre_test_id=test_centre_test.id,
            appointment_time=datetime.now(timezone.utc) + timedelta(days=1),
            total_amount=test_centre_test.price,
            status=BookingStatus.PENDING,
        )
        db.add(booking)
        db.commit()
        db.refresh(booking)

        payment = Payment(
            booking_id=booking.id,
            idempotency_key=str(uuid.uuid4()),
            transaction_reference=f"txn_{uuid.uuid4().hex[:12]}",
            amount=booking.total_amount,
            status=PaymentStatus.INITIATED,
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        with patch.object(settings, "ENABLE_WEBHOOK_HMAC", True):
            payload = {
                "event_id": f"evt_{uuid.uuid4().hex}",
                "event_type": "payment.succeeded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "transaction_reference": payment.transaction_reference,
                    "booking_id": str(booking.id),
                    "amount": float(booking.total_amount),
                    "status": "SUCCESS",
                },
            }
            raw_body = json.dumps(payload).encode("utf-8")
            valid_sig = compute_hmac_signature(raw_body, settings.WEBHOOK_SECRET_KEY)
            headers = {
                SIGNATURE_HEADER: valid_sig,
                "Content-Type": "application/json",
            }

            response = client.post("/api/v1/payments/webhook", content=raw_body, headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "processed"
            assert data["event_id"] == payload["event_id"]

            db.refresh(booking)
            assert booking.status == BookingStatus.CONFIRMED


class TestCeleryBackgroundTasks:
    """Direct tests for Celery task functions."""

    def test_send_booking_notification_confirmed(self):
        result = send_booking_notification(
            booking_id="b-1234-test",
            user_email="patient@example.com",
            user_name="John Doe",
            booking_status="CONFIRMED",
            amount=799.0,
            appointment_time="2026-10-15T10:00:00Z",
        )
        assert result["status"] == "sent"
        assert result["channel"] == "email+sms"
        assert result["booking_id"] == "b-1234-test"
        assert "CONFIRMED" in result["message"]

    def test_send_booking_notification_failed(self):
        result = send_booking_notification(
            booking_id="b-5678-test",
            user_email="patient@example.com",
            user_name="John Doe",
            booking_status="FAILED",
            amount=799.0,
            appointment_time="2026-10-15T10:00:00Z",
        )
        assert result["status"] == "sent"
        assert "FAILED" in result["message"] or "payment failure" in result["message"].lower()

    def test_auto_cancel_stale_bookings(self, db, test_centre_test, test_user):
        """Test scanning and auto-cancelling stale PENDING bookings."""
        stale_booking = Booking(
            user_id=test_user.id,
            centre_test_id=test_centre_test.id,
            appointment_time=datetime.now(timezone.utc) + timedelta(days=2),
            total_amount=test_centre_test.price,
            status=BookingStatus.PENDING,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        )
        db.add(stale_booking)
        db.commit()
        db.refresh(stale_booking)

        with patch("app.db.session.SessionLocal", return_value=db), patch.object(db, "close"):
            result = auto_cancel_stale_bookings()
            assert "cancelled_count" in result
            assert result["cancelled_count"] >= 1

            updated = db.query(Booking).filter(Booking.id == stale_booking.id).first()
            assert updated.status == BookingStatus.CANCELLED


class TestCacheUtilities:
    """Tests for Redis cache keys and fallback helpers."""

    def test_cache_key_generation(self):
        k1 = make_centres_cache_key("Delhi", True, 1, 20)
        k2 = make_centres_cache_key("Delhi", True, 1, 20)
        k3 = make_centres_cache_key("Mumbai", True, 1, 20)

        assert k1 == k2
        assert k1 != k3
        assert k1.startswith("eve:cache:")

        kt1 = make_tests_cache_key("Blood", "CBC", 1, 10)
        kt2 = make_tests_cache_key("Blood", "CBC", 1, 10)
        assert kt1 == kt2

        kc = make_centre_tests_cache_key("centre-uuid-1")
        assert kc.startswith("eve:cache:")

    def test_cache_graceful_fallback(self):
        val = cache_get("nonexistent_test_key_123")
        assert val is None
        invalidate_centre_cache()
