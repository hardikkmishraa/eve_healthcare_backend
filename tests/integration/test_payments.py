"""
Integration tests for Payment simulation and Webhook idempotency.

Critical test cases:
- Successful and failed payment simulations
- Duplicate webhook delivery (same event_id) → must be safely ignored (HTTP 200)
- Triple webhook delivery → still idempotent
- Out-of-order webhook delivery (FAILED after already CONFIRMED) → disallowed
- Concurrent-like sequential delivery of identical events
- Invalid booking/payment references in webhook
"""
import pytest
import uuid
from datetime import datetime, timedelta, timezone


def future_appointment(hours_ahead: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).isoformat()


def create_booking(client, auth_headers, test_centre_test):
    """Helper to create a booking and return its response."""
    return client.post("/api/v1/bookings", json={
        "centre_test_id": test_centre_test.id,
        "appointment_time": future_appointment(3),
    }, headers=auth_headers)


def build_webhook_payload(transaction_reference: str, booking_id: str, amount: float,
                           status: str = "SUCCESS", event_id: str = None) -> dict:
    return {
        "event_id": event_id or f"evt_{uuid.uuid4().hex}",
        "event_type": "payment.updated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "transaction_reference": transaction_reference,
            "booking_id": booking_id,
            "amount": amount,
            "currency": "INR",
            "status": status,
            "failure_reason": None if status == "SUCCESS" else "Simulated decline",
        },
    }


class TestPaymentSimulation:
    def test_simulate_payment_success(self, client, auth_headers, test_centre_test):
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        response = client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "SUCCESS",
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["payment_status"] == "SUCCESS"
        assert data["booking_status"] == "CONFIRMED"
        assert data["booking_id"] == booking_id
        assert "transaction_reference" in data
        assert data["transaction_reference"].startswith("txn_mock_")

    def test_simulate_payment_failure(self, client, auth_headers, test_centre_test):
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        response = client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "FAILED",
        }, headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["payment_status"] == "FAILED"
        assert data["booking_status"] == "FAILED"

    def test_cannot_pay_for_nonexistent_booking(self, client, auth_headers):
        response = client.post("/api/v1/payments/", json={
            "booking_id": "00000000-0000-0000-0000-000000000000",
            "force_status": "SUCCESS",
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_cannot_pay_for_already_confirmed_booking(self, client, auth_headers, test_centre_test):
        """Payment on an already-confirmed booking (non-PENDING) should be rejected."""
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        # First payment — confirm it
        client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "SUCCESS",
        }, headers=auth_headers)

        # Attempt to pay again on a CONFIRMED booking
        second_response = client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "SUCCESS",
        }, headers=auth_headers)
        assert second_response.status_code == 400

    def test_cannot_pay_for_other_users_booking(
        self, client, auth_headers, another_auth_headers, test_centre_test
    ):
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        response = client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "SUCCESS",
        }, headers=another_auth_headers)
        assert response.status_code == 404  # Prevents ID enumeration

    def test_payment_unauthenticated(self, client, test_centre_test):
        response = client.post("/api/v1/payments/", json={
            "booking_id": "some-id",
            "force_status": "SUCCESS",
        })
        assert response.status_code == 403


class TestWebhookIdempotency:
    def _create_pending_payment(self, client, auth_headers, test_centre_test):
        """Create a booking and simulate a payment; return (booking_id, txn_ref)."""
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]
        pay_resp = client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "SUCCESS",
        }, headers=auth_headers)
        txn_ref = pay_resp.json()["transaction_reference"]
        amount = pay_resp.json()["amount"]
        return booking_id, txn_ref, amount

    def test_webhook_success_updates_booking(self, client, auth_headers, db, test_centre_test):
        """A fresh webhook should update booking to CONFIRMED."""
        # Create booking and get pending payment via direct DB manipulation for a clean state
        from app.models.models import Booking, BookingStatus, Payment, PaymentStatus
        from decimal import Decimal
        import uuid as _uuid

        booking = Booking(
            user_id=auth_headers["Authorization"].split()[1],  # won't work, use fixture instead
        )
        # Use the simulate endpoint as the "gateway trigger" instead
        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        # Directly insert a pending payment record for webhook testing
        from tests.conftest import TestingSessionLocal
        test_db = TestingSessionLocal()
        txn_ref = f"txn_webhook_{_uuid.uuid4().hex[:8].upper()}"
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=str(_uuid.uuid4()),
            transaction_reference=txn_ref,
            amount=Decimal("550.00"),
            status=PaymentStatus.INITIATED,
        )
        test_db.add(payment)
        test_db.commit()
        test_db.close()

        event_id = f"evt_{_uuid.uuid4().hex}"
        payload = build_webhook_payload(txn_ref, booking_id, 550.00, "SUCCESS", event_id)

        response = client.post("/api/v1/payments/webhook", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["event_id"] == event_id

        # Verify booking is now CONFIRMED
        booking_detail = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert booking_detail.json()["status"] == "CONFIRMED"

    def test_webhook_duplicate_is_ignored(self, client, auth_headers, test_centre_test):
        """
        *** CRITICAL IDEMPOTENCY TEST ***
        Same event_id delivered twice must not produce duplicate processing.
        Second delivery must return 200 with status='ignored'.
        """
        from app.models.models import Payment, PaymentStatus
        from decimal import Decimal
        import uuid as _uuid
        from tests.conftest import TestingSessionLocal

        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        test_db = TestingSessionLocal()
        txn_ref = f"txn_dup_{_uuid.uuid4().hex[:8].upper()}"
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=str(_uuid.uuid4()),
            transaction_reference=txn_ref,
            amount=Decimal("550.00"),
            status=PaymentStatus.INITIATED,
        )
        test_db.add(payment)
        test_db.commit()
        test_db.close()

        # Use the SAME event_id for both deliveries
        shared_event_id = f"evt_{_uuid.uuid4().hex}"
        payload = build_webhook_payload(txn_ref, booking_id, 550.00, "SUCCESS", shared_event_id)

        # First delivery — should process
        first_response = client.post("/api/v1/payments/webhook", json=payload)
        assert first_response.status_code == 200
        assert first_response.json()["status"] == "processed"

        # Second delivery (same event_id) — must be silently ignored
        second_response = client.post("/api/v1/payments/webhook", json=payload)
        assert second_response.status_code == 200
        assert second_response.json()["status"] == "ignored"

        # Verify booking only processed once (still CONFIRMED, not doubly updated)
        booking_detail = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert booking_detail.json()["status"] == "CONFIRMED"

    def test_webhook_triple_delivery_idempotent(self, client, auth_headers, test_centre_test):
        """Same event delivered 3 times — only first processes, next two are ignored."""
        from app.models.models import Payment, PaymentStatus
        from decimal import Decimal
        import uuid as _uuid
        from tests.conftest import TestingSessionLocal

        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        test_db = TestingSessionLocal()
        txn_ref = f"txn_triple_{_uuid.uuid4().hex[:8].upper()}"
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=str(_uuid.uuid4()),
            transaction_reference=txn_ref,
            amount=Decimal("550.00"),
            status=PaymentStatus.INITIATED,
        )
        test_db.add(payment)
        test_db.commit()
        test_db.close()

        shared_event_id = f"evt_{_uuid.uuid4().hex}"
        payload = build_webhook_payload(txn_ref, booking_id, 550.00, "SUCCESS", shared_event_id)

        statuses = []
        for _ in range(3):
            resp = client.post("/api/v1/payments/webhook", json=payload)
            assert resp.status_code == 200
            statuses.append(resp.json()["status"])

        assert statuses[0] == "processed"
        assert statuses[1] == "ignored"
        assert statuses[2] == "ignored"

    def test_webhook_out_of_order_fail_after_confirm(self, client, auth_headers, test_centre_test):
        """
        Out-of-order delivery: FAILED webhook arrives after booking is already CONFIRMED.
        Must be gracefully ignored (status='ignored'), booking stays CONFIRMED.
        """
        from app.models.models import Payment, PaymentStatus
        from decimal import Decimal
        import uuid as _uuid
        from tests.conftest import TestingSessionLocal

        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        test_db = TestingSessionLocal()
        txn_ref = f"txn_ooo_{_uuid.uuid4().hex[:8].upper()}"
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=str(_uuid.uuid4()),
            transaction_reference=txn_ref,
            amount=Decimal("550.00"),
            status=PaymentStatus.INITIATED,
        )
        test_db.add(payment)
        test_db.commit()
        test_db.close()

        # First: webhook confirms the booking
        success_payload = build_webhook_payload(txn_ref, booking_id, 550.00, "SUCCESS")
        client.post("/api/v1/payments/webhook", json=success_payload)

        # Verify CONFIRMED
        booking_detail = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert booking_detail.json()["status"] == "CONFIRMED"

        # Now, late-arriving FAILED webhook with a different event_id
        failed_payload = build_webhook_payload(txn_ref, booking_id, 550.00, "FAILED")
        failed_response = client.post("/api/v1/payments/webhook", json=failed_payload)

        assert failed_response.status_code == 200
        assert failed_response.json()["status"] == "ignored"

        # Booking must STILL be CONFIRMED — not regressed to FAILED
        booking_detail = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert booking_detail.json()["status"] == "CONFIRMED"

    def test_webhook_invalid_transaction_reference(self, client):
        """Webhook referencing a non-existent transaction_reference should return 404."""
        payload = build_webhook_payload(
            transaction_reference="txn_nonexistent_12345",
            booking_id="00000000-0000-0000-0000-000000000000",
            amount=500.00,
        )
        response = client.post("/api/v1/payments/webhook", json=payload)
        assert response.status_code == 404

    def test_webhook_missing_event_id(self, client):
        """Webhook payload without event_id should return 422."""
        response = client.post("/api/v1/payments/webhook", json={
            "event_type": "payment.updated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "transaction_reference": "txn_123",
                "booking_id": "some-id",
                "amount": 500.00,
                "status": "SUCCESS",
            }
        })
        assert response.status_code == 422

    def test_webhook_concurrent_duplicate_delivery(self, client, auth_headers, test_centre_test):
        """
        Concurrent duplicate webhook events (simultaneous retries) must both succeed with HTTP 200.
        One processes, one is safely ignored — no 500 IntegrityError or race condition.
        """
        from concurrent.futures import ThreadPoolExecutor
        from app.models.models import Payment, PaymentStatus
        from decimal import Decimal
        from tests.conftest import TestingSessionLocal

        booking_resp = create_booking(client, auth_headers, test_centre_test)
        booking_id = booking_resp.json()["id"]

        test_db = TestingSessionLocal()
        txn_ref = f"txn_conc_{uuid.uuid4().hex[:8].upper()}"
        payment = Payment(
            booking_id=booking_id,
            idempotency_key=str(uuid.uuid4()),
            transaction_reference=txn_ref,
            amount=Decimal("550.00"),
            status=PaymentStatus.INITIATED,
        )
        test_db.add(payment)
        test_db.commit()
        test_db.close()

        shared_event_id = f"evt_conc_{uuid.uuid4().hex}"
        payload = build_webhook_payload(txn_ref, booking_id, 550.00, "SUCCESS", shared_event_id)

        def send_webhook():
            return client.post("/api/v1/payments/webhook", json=payload)

        with ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(send_webhook)
            f2 = executor.submit(send_webhook)
            r1, r2 = f1.result(), f2.result()

        assert r1.status_code == 200
        assert r2.status_code == 200
        statuses = sorted([r1.json()["status"], r2.json()["status"]])
        assert statuses == ["ignored", "processed"]

        # Final state check
        booking_detail = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert booking_detail.json()["status"] == "CONFIRMED"

