"""Integration tests for the full booking lifecycle."""
import pytest
from datetime import datetime, timedelta, timezone


def future_appointment(hours_ahead: int = 3) -> str:
    """Return an ISO 8601 datetime string hours_ahead in the future."""
    return (datetime.now(timezone.utc) + timedelta(hours=hours_ahead)).isoformat()


class TestCreateBooking:
    def test_create_booking_success(self, client, auth_headers, test_centre_test):
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
            "notes": "Please call before arrival",
        }, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "PENDING"
        assert data["centre_test_id"] == test_centre_test.id
        # Server-side amount: must equal the DB price, not whatever the client sent
        assert float(data["total_amount"]) == 550.00

    def test_create_booking_unauthenticated(self, client, test_centre_test):
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        })
        assert response.status_code == 403

    def test_create_booking_past_appointment(self, client, auth_headers, test_centre_test):
        """Appointment time in the past should be rejected."""
        past_time = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": past_time,
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_create_booking_appointment_too_soon(self, client, auth_headers, test_centre_test):
        """Appointment less than 1 hour away should be rejected."""
        too_soon = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": too_soon,
        }, headers=auth_headers)
        assert response.status_code == 422

    def test_create_booking_invalid_centre_test_id(self, client, auth_headers):
        """Non-existent centre_test_id should return 404."""
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": "00000000-0000-0000-0000-000000000000",
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        assert response.status_code == 404

    def test_create_booking_unavailable_test(self, client, auth_headers, test_centre_test_unavailable):
        """Booking for an unavailable test should return 400."""
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test_unavailable.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "unavailable" in response.json()["detail"].lower()

    def test_create_booking_inactive_centre(self, client, auth_headers, db, test_centre_inactive, test_diagnostic_test):
        """Booking at an inactive centre should return 400."""
        from app.models.models import CentreTest
        from decimal import Decimal
        ct = CentreTest(
            centre_id=test_centre_inactive.id,
            test_id=test_diagnostic_test.id,
            price=Decimal("500.00"),
        )
        db.add(ct)
        db.commit()
        db.refresh(ct)
        response = client.post("/api/v1/bookings", json={
            "centre_test_id": ct.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        assert response.status_code == 400
        assert "inactive" in response.json()["detail"].lower()


class TestGetBooking:
    def test_get_own_booking(self, client, auth_headers, test_centre_test):
        # Create a booking
        create_resp = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        booking_id = create_resp.json()["id"]

        # Retrieve it
        response = client.get(f"/api/v1/bookings/{booking_id}", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["id"] == booking_id

    def test_cannot_access_other_users_booking(
        self, client, auth_headers, another_auth_headers, test_centre_test
    ):
        """User A's booking should return 404 when accessed by User B (prevents enumeration)."""
        create_resp = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        booking_id = create_resp.json()["id"]

        # Another user tries to view User A's booking
        response = client.get(f"/api/v1/bookings/{booking_id}", headers=another_auth_headers)
        assert response.status_code == 404  # NOT 403, prevents ID enumeration

    def test_get_nonexistent_booking(self, client, auth_headers):
        response = client.get(
            "/api/v1/bookings/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert response.status_code == 404


class TestListBookings:
    def test_list_my_bookings(self, client, auth_headers, test_centre_test):
        # Create 2 bookings
        for _ in range(2):
            client.post("/api/v1/bookings", json={
                "centre_test_id": test_centre_test.id,
                "appointment_time": future_appointment(3),
            }, headers=auth_headers)

        response = client.get("/api/v1/bookings/my", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["results"]) == 2

    def test_list_bookings_pagination(self, client, auth_headers, test_centre_test):
        for _ in range(5):
            client.post("/api/v1/bookings", json={
                "centre_test_id": test_centre_test.id,
                "appointment_time": future_appointment(3),
            }, headers=auth_headers)

        response = client.get("/api/v1/bookings/my?page=1&page_size=3", headers=auth_headers)
        data = response.json()
        assert data["total"] == 5
        assert len(data["results"]) == 3


class TestCancelBooking:
    def test_cancel_pending_booking(self, client, auth_headers, test_centre_test):
        create_resp = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        booking_id = create_resp.json()["id"]
        assert create_resp.json()["status"] == "PENDING"

        cancel_resp = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=auth_headers)
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"

    def test_cannot_cancel_failed_booking(self, client, auth_headers, test_centre_test):
        """FAILED is a terminal state; cancel should return 409."""
        create_resp = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        booking_id = create_resp.json()["id"]

        # Force payment failure to put booking in FAILED state
        client.post("/api/v1/payments/", json={
            "booking_id": booking_id,
            "force_status": "FAILED",
        }, headers=auth_headers)

        # Try to cancel the now-FAILED booking
        cancel_resp = client.post(f"/api/v1/bookings/{booking_id}/cancel", headers=auth_headers)
        assert cancel_resp.status_code == 409

    def test_cannot_cancel_other_users_booking(
        self, client, auth_headers, another_auth_headers, test_centre_test
    ):
        create_resp = client.post("/api/v1/bookings", json={
            "centre_test_id": test_centre_test.id,
            "appointment_time": future_appointment(3),
        }, headers=auth_headers)
        booking_id = create_resp.json()["id"]

        cancel_resp = client.post(
            f"/api/v1/bookings/{booking_id}/cancel",
            headers=another_auth_headers,
        )
        assert cancel_resp.status_code == 404  # 404 to prevent ID enumeration
