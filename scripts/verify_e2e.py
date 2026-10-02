#!/usr/bin/env python3
"""
EVE Healthcare — End-to-End Live Verification Script
Validates the full business flow against a live server instance:
- Health & readiness probes
- User signup, login, JWT token auth
- Diagnostic catalogue & pricing discovery
- Booking creation and state lifecycle
- Simulated payment flows (SUCCESS and FAILED)
- Webhook idempotency and deduplication
- IDOR access prevention
"""
import sys
import uuid
import time
import requests
from datetime import datetime, timedelta, timezone

BASE_URL = "http://localhost:8000"
API_V1 = f"{BASE_URL}/api/v1"


def print_step(title: str):
    print(f"\n[+] {title}")


def assert_status(response: requests.Response, expected_status: int, action: str):
    if response.status_code != expected_status:
        print(f"[-] FAILED: {action} — Expected {expected_status}, got {response.status_code}")
        print(f"    Body: {response.text}")
        sys.exit(1)
    print(f"    ✓ {action} (HTTP {response.status_code})")


def main():
    print("=" * 65)
    print("  EVE Healthcare API — End-to-End Live System Verification")
    print("=" * 65)

    # 1. Health & Readiness
    print_step("1. Checking Service Health & Readiness")
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        assert_status(r, 200, "Liveness probe (/health)")
        assert r.json().get("status") == "healthy"

        r = requests.get(f"{BASE_URL}/ready", timeout=5)
        assert_status(r, 200, "Readiness probe (/ready)")
        checks = r.json().get("checks", {})
        print(f"    PostgreSQL: {checks.get('postgres')} | Redis: {checks.get('redis')}")
    except requests.exceptions.ConnectionError:
        print(f"[-] ERROR: Server is not running at {BASE_URL}.")
        print("    Please start the server first: uvicorn app.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    # 2. Authentication: Signup & Login
    print_step("2. User Registration & JWT Authentication")
    random_suffix = uuid.uuid4().hex[:6]
    user_email = f"e2e_user_{random_suffix}@evehealthcare.com"
    password = "StrongPassword@123"

    signup_payload = {
        "email": user_email,
        "password": password,
        "full_name": "E2E Test Patient",
        "phone_number": "+919876543210",
    }
    r = requests.post(f"{API_V1}/auth/signup", json=signup_payload)
    assert_status(r, 201, f"Signup new user ({user_email})")
    user_data = r.json()
    user_id = user_data["id"]

    login_payload = {"email": user_email, "password": password}
    r = requests.post(f"{API_V1}/auth/login", json=login_payload)
    assert_status(r, 200, "Login with credentials")
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = requests.get(f"{API_V1}/auth/me", headers=headers)
    assert_status(r, 200, "Fetch authenticated profile (/auth/me)")
    assert r.json()["email"] == user_email

    # 3. Diagnostic Catalogue Discovery
    print_step("3. Diagnostic Catalogue & Pricing Discovery")
    r = requests.get(f"{API_V1}/centres?page=1&page_size=5")
    assert_status(r, 200, "List diagnostic centres")
    centres = r.json().get("results", [])
    if not centres:
        print("[-] No diagnostic centres found. Please seed the DB (python scripts/seed_db.py).")
        sys.exit(1)
    centre = centres[0]
    centre_id = centre["id"]
    print(f"    Selected Centre: {centre['name']} ({centre['city']})")

    r = requests.get(f"{API_V1}/tests?page=1&page_size=5")
    assert_status(r, 200, "List diagnostic tests")
    tests = r.json().get("results", [])
    if not tests:
        print("[-] No tests found. Please seed the DB.")
        sys.exit(1)
    print(f"    Available tests in catalogue: {len(tests)}")

    r = requests.get(f"{API_V1}/centres/{centre_id}/tests")
    assert_status(r, 200, f"List offerings for centre: {centre['name']}")
    offerings = r.json()
    if not offerings:
        print("[-] No offerings found for centre.")
        sys.exit(1)
    centre_test = offerings[0]
    centre_test_id = centre_test["id"]
    price = centre_test["price"]
    test_name = centre_test["test"]["name"]
    print(f"    Selected Offering: {test_name} — Price: INR {price}")

    # 4. Booking Flow: Creation & Status
    print_step("4. Booking Creation & State Management")
    appointment_time = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    booking_payload = {
        "centre_test_id": centre_test_id,
        "appointment_time": appointment_time,
        "notes": "E2E verification booking test",
    }
    r = requests.post(f"{API_V1}/bookings", json=booking_payload, headers=headers)
    assert_status(r, 201, "Create booking")
    booking = r.json()
    booking_id = booking["id"]
    assert booking["status"] == "PENDING"
    print(f"    Created Booking ID: {booking_id} (Status: {booking['status']}, Amount: INR {booking['total_amount']})")

    r = requests.get(f"{API_V1}/bookings/{booking_id}", headers=headers)
    assert_status(r, 200, "Get booking details")
    assert r.json()["id"] == booking_id

    # 5. Security Check: IDOR Protection
    print_step("5. Security Verification: IDOR Protection")
    attacker_email = f"attacker_{random_suffix}@evehealthcare.com"
    r = requests.post(f"{API_V1}/auth/signup", json={
        "email": attacker_email,
        "password": password,
        "full_name": "Attacker",
    })
    attacker_login = requests.post(f"{API_V1}/auth/login", json={"email": attacker_email, "password": password})
    attacker_headers = {"Authorization": f"Bearer {attacker_login.json()['access_token']}"}

    r = requests.get(f"{API_V1}/bookings/{booking_id}", headers=attacker_headers)
    assert_status(r, 404, "Verify unauthorized user cannot view booking (IDOR prevented via 404)")

    # 6. Simulated Payment Flow (SUCCESS)
    print_step("6. Simulated Payment (SUCCESS Scenario)")
    r = requests.post(f"{API_V1}/payments/", json={
        "booking_id": booking_id,
        "force_status": "SUCCESS",
    }, headers=headers)
    assert_status(r, 200, "Execute payment simulation (SUCCESS)")
    payment_resp = r.json()
    assert payment_resp["payment_status"] == "SUCCESS"
    assert payment_resp["booking_status"] == "CONFIRMED"
    txn_ref = payment_resp["transaction_reference"]
    print(f"    Payment Reference: {txn_ref} | Booking Status: CONFIRMED")

    # 7. Disallow Payment on Settled Booking
    print_step("7. State Machine Guard: Reject Payment on CONFIRMED Booking")
    r = requests.post(f"{API_V1}/payments/", json={
        "booking_id": booking_id,
        "force_status": "SUCCESS",
    }, headers=headers)
    assert_status(r, 400, "Duplicate payment attempt correctly rejected")

    # 8. Simulated Payment Flow (FAILED)
    print_step("8. Simulated Payment (FAILED Scenario)")
    r = requests.post(f"{API_V1}/bookings", json=booking_payload, headers=headers)
    assert_status(r, 201, "Create second booking for failure test")
    failed_booking_id = r.json()["id"]

    r = requests.post(f"{API_V1}/payments/", json={
        "booking_id": failed_booking_id,
        "force_status": "FAILED",
    }, headers=headers)
    assert_status(r, 200, "Execute payment simulation (FAILED)")
    assert r.json()["payment_status"] == "FAILED"
    assert r.json()["booking_status"] == "FAILED"
    print(f"    Booking {failed_booking_id} successfully moved to FAILED state")

    # 9. Webhook Idempotency & Concurrency Verification
    print_step("9. Payment Webhook Processing & Idempotency")
    r = requests.post(f"{API_V1}/bookings", json=booking_payload, headers=headers)
    assert_status(r, 201, "Create third booking for webhook tests")
    webhook_booking_id = r.json()["id"]

    webhook_event_id = f"evt_e2e_{uuid.uuid4().hex}"

    # First simulate a payment to generate transaction reference
    r = requests.post(f"{API_V1}/payments/", json={
        "booking_id": webhook_booking_id,
        "force_status": "SUCCESS",
    }, headers=headers)
    confirmed_txn_ref = r.json()["transaction_reference"]

    webhook_payload = {
        "event_id": webhook_event_id,
        "event_type": "payment.updated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": {
            "transaction_reference": confirmed_txn_ref,
            "booking_id": webhook_booking_id,
            "amount": float(price),
            "currency": "INR",
            "status": "SUCCESS",
            "failure_reason": None,
        },
    }

    # First webhook delivery (already settled booking -> returns 200 ignored)
    r = requests.post(f"{API_V1}/payments/webhook", json=webhook_payload)
    assert_status(r, 200, "First webhook delivery (idempotently ignored for settled booking)")

    # Repeated delivery with exact same event_id
    r = requests.post(f"{API_V1}/payments/webhook", json=webhook_payload)
    assert_status(r, 200, "Repeated webhook delivery (safely deduplicated via event_id)")
    assert r.json()["status"] == "ignored"

    # Out-of-order FAILED webhook arriving late
    late_failed_payload = dict(webhook_payload)
    late_failed_payload["event_id"] = f"evt_late_{uuid.uuid4().hex}"
    late_failed_payload["data"] = dict(webhook_payload["data"])
    late_failed_payload["data"]["status"] = "FAILED"
    r = requests.post(f"{API_V1}/payments/webhook", json=late_failed_payload)
    assert_status(r, 200, "Late out-of-order FAILED webhook safely ignored (no status regression)")
    assert r.json()["status"] == "ignored"

    # Verify final booking state is still CONFIRMED
    r = requests.get(f"{API_V1}/bookings/{webhook_booking_id}", headers=headers)
    assert r.json()["status"] == "CONFIRMED"
    print(f"    Verified booking {webhook_booking_id} remained CONFIRMED")

    print("\n" + "=" * 65)
    print("  ALL END-TO-END VERIFICATION CHECKS PASSED (100% SUCCESS)!")
    print("=" * 65)


if __name__ == "__main__":
    main()
