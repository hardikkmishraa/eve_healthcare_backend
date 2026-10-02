"""Unit tests for Authentication endpoints."""
import pytest


class TestSignup:
    def test_signup_success(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "email": "newuser@test.com",
            "password": "NewUser@1234",
            "full_name": "New User",
            "phone_number": "+911234567890",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@test.com"
        assert data["full_name"] == "New User"
        assert data["role"] == "PATIENT"
        assert "id" in data
        assert "hashed_password" not in data  # never expose hashed password

    def test_signup_duplicate_email(self, client, test_user):
        response = client.post("/api/v1/auth/signup", json={
            "email": "patient@test.com",  # already exists
            "password": "Another@1234",
            "full_name": "Duplicate User",
        })
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_signup_weak_password_no_uppercase(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "email": "weak@test.com",
            "password": "nouppercasepass1",
            "full_name": "Weak Password User",
        })
        assert response.status_code == 422

    def test_signup_weak_password_no_digit(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "email": "weak2@test.com",
            "password": "NoDigitHere!",
            "full_name": "Weak Password User",
        })
        assert response.status_code == 422

    def test_signup_invalid_email(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "email": "not-an-email",
            "password": "Password@123",
            "full_name": "Bad Email",
        })
        assert response.status_code == 422

    def test_signup_password_too_short(self, client):
        response = client.post("/api/v1/auth/signup", json={
            "email": "short@test.com",
            "password": "Ab1",
            "full_name": "Short Pass",
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": "patient@test.com",
            "password": "Patient@1234",
        })
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0

    def test_login_wrong_password(self, client, test_user):
        response = client.post("/api/v1/auth/login", json={
            "email": "patient@test.com",
            "password": "WrongPassword@1",
        })
        assert response.status_code == 401
        assert "Invalid email or password" in response.json()["detail"]

    def test_login_nonexistent_user(self, client):
        response = client.post("/api/v1/auth/login", json={
            "email": "nobody@test.com",
            "password": "Nobody@1234",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client):
        response = client.post("/api/v1/auth/login", json={"email": "test@test.com"})
        assert response.status_code == 422


class TestGetMe:
    def test_get_me_success(self, client, test_user, auth_headers):
        response = client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "patient@test.com"
        assert data["full_name"] == "Test Patient"

    def test_get_me_no_token(self, client):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 403  # HTTPBearer raises 403 when no token

    def test_get_me_invalid_token(self, client):
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert response.status_code == 401
