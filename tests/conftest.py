"""
Shared pytest fixtures for all tests.
Uses a separate test database that is created fresh for each test session.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import get_db
from app.models.models import Base, User, DiagnosticCentre, DiagnosticTest, CentreTest, UserRole
from app.core.security import hash_password
from app.core.cache import limiter
from decimal import Decimal

# Disable rate limiter for testing suite
limiter.enabled = False

# Use a separate SQLite in-memory database for testing (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite:///./test_eve_healthcare.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function", autouse=True)
def setup_database():
    """Create all tables before each test, drop after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db():
    """Direct DB session for fixtures that need to insert data."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


# ─── User Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def test_user(db):
    """Create a standard patient user."""
    user = User(
        email="patient@test.com",
        hashed_password=hash_password("Patient@1234"),
        full_name="Test Patient",
        phone_number="+911234567890",
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_admin(db):
    """Create an admin user."""
    admin = User(
        email="admin@test.com",
        hashed_password=hash_password("Admin@1234"),
        full_name="Test Admin",
        role=UserRole.ADMIN,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


@pytest.fixture
def another_user(db):
    """A second patient user (for authorization boundary testing)."""
    user = User(
        email="other@test.com",
        hashed_password=hash_password("Other@1234"),
        full_name="Other Patient",
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ─── Auth Token Helpers ────────────────────────────────────────────────────────

@pytest.fixture
def user_token(client, test_user):
    """Get JWT token for test_user."""
    response = client.post("/api/v1/auth/login", json={
        "email": "patient@test.com",
        "password": "Patient@1234",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def another_user_token(client, another_user):
    """Get JWT token for another_user."""
    response = client.post("/api/v1/auth/login", json={
        "email": "other@test.com",
        "password": "Other@1234",
    })
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(user_token):
    return {"Authorization": f"Bearer {user_token}"}


@pytest.fixture
def another_auth_headers(another_user_token):
    return {"Authorization": f"Bearer {another_user_token}"}


# ─── Catalogue Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def test_centre(db):
    """Create a test diagnostic centre."""
    centre = DiagnosticCentre(
        name="Test Medical Centre",
        address="123 Test Street",
        city="Mumbai",
        pincode="400001",
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@pytest.fixture
def test_centre_inactive(db):
    """Create an inactive test diagnostic centre."""
    centre = DiagnosticCentre(
        name="Closed Centre",
        address="456 Old Street",
        city="Delhi",
        pincode="110001",
        is_active=False,
    )
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


@pytest.fixture
def test_diagnostic_test(db):
    """Create a test diagnostic test."""
    test = DiagnosticTest(
        name="Complete Blood Count",
        category="Haematology",
        description="Blood cell count test",
        sample_type="Blood",
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@pytest.fixture
def test_centre_test(db, test_centre, test_diagnostic_test):
    """Create a centre-test mapping (a test offered at a centre with pricing)."""
    ct = CentreTest(
        centre_id=test_centre.id,
        test_id=test_diagnostic_test.id,
        price=Decimal("550.00"),
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct


@pytest.fixture
def test_centre_test_unavailable(db, test_centre, test_diagnostic_test):
    """Create an unavailable centre-test mapping."""
    ct = CentreTest(
        centre_id=test_centre.id,
        test_id=test_diagnostic_test.id,
        price=Decimal("550.00"),
        is_available=False,
    )
    db.add(ct)
    db.commit()
    db.refresh(ct)
    return ct
