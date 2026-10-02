"""
Integration tests for the Diagnostic Centres and Diagnostic Tests catalogue API.
Tests listing, filtering, pagination, creation, centre offerings, and error cases.
"""
import pytest
from decimal import Decimal
from app.models.models import DiagnosticCentre, DiagnosticTest, CentreTest
from app.core.cache import invalidate_centre_cache


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Redis cache before each catalogue test."""
    invalidate_centre_cache()
    yield
    invalidate_centre_cache()


class TestCentresCatalogue:
    """Tests for /api/v1/centres endpoints."""

    def test_list_centres_empty(self, client):
        response = client.get("/api/v1/centres")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "total" in data
        assert data["total"] == 0

    def test_list_centres_populated(self, client, test_centre):
        response = client.get("/api/v1/centres")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        centre_names = [c["name"] for c in data["results"]]
        assert test_centre.name in centre_names

    def test_list_centres_city_filter(self, client, db):
        c1 = DiagnosticCentre(name="Centre South", address="100 Ring Rd", city="Bangalore", pincode="560001", is_active=True)
        c2 = DiagnosticCentre(name="Centre North", address="200 Park St", city="Delhi", pincode="110001", is_active=True)
        db.add_all([c1, c2])
        db.commit()

        # Filter by Bangalore
        res_blr = client.get("/api/v1/centres?city=Bangalore")
        assert res_blr.status_code == 200
        items_blr = res_blr.json()["results"]
        assert all(c["city"] == "Bangalore" for c in items_blr)
        assert any(c["name"] == "Centre South" for c in items_blr)

        # Filter by Delhi
        res_del = client.get("/api/v1/centres?city=Delhi")
        assert res_del.status_code == 200
        items_del = res_del.json()["results"]
        assert all(c["city"] == "Delhi" for c in items_del)

    def test_get_centre_by_id(self, client, test_centre):
        response = client.get(f"/api/v1/centres/{test_centre.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_centre.id)
        assert data["name"] == test_centre.name
        assert data["city"] == test_centre.city

    def test_get_nonexistent_centre(self, client):
        import uuid
        random_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/centres/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_centre_success(self, client, auth_headers):
        payload = {
            "name": "Metropolis Healthcare",
            "address": "456 Hospital Road",
            "city": "Mumbai",
            "pincode": "400001",
            "is_active": True,
        }
        response = client.post("/api/v1/centres", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Metropolis Healthcare"
        assert data["city"] == "Mumbai"
        assert "id" in data

    def test_create_centre_unauthenticated(self, client):
        payload = {
            "name": "Unauthorized Lab",
            "address": "No Auth Road",
            "city": "Nowhere",
            "pincode": "000000",
        }
        response = client.post("/api/v1/centres", json=payload)
        assert response.status_code in [401, 403]


class TestTestsCatalogue:
    """Tests for /api/v1/tests endpoints."""

    def test_list_tests_empty(self, client):
        response = client.get("/api/v1/tests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["results"] == []

    def test_list_tests_with_items(self, client, test_diagnostic_test):
        response = client.get("/api/v1/tests")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        assert any(t["name"] == test_diagnostic_test.name for t in data["results"])

    def test_filter_tests_by_category_and_search(self, client, db):
        t1 = DiagnosticTest(name="Complete Blood Count (CBC)", category="Pathology", description="Blood profile", sample_type="Blood")
        t2 = DiagnosticTest(name="Chest X-Ray", category="Radiology", description="Chest imaging", sample_type="None")
        t3 = DiagnosticTest(name="Lipid Profile", category="Pathology", description="Cholesterol panel", sample_type="Blood")
        db.add_all([t1, t2, t3])
        db.commit()

        # Category filter
        res_cat = client.get("/api/v1/tests?category=Radiology")
        assert res_cat.status_code == 200
        items_cat = res_cat.json()["results"]
        assert len(items_cat) == 1
        assert items_cat[0]["name"] == "Chest X-Ray"

        # Search filter
        res_search = client.get("/api/v1/tests?search=Lipid")
        assert res_search.status_code == 200
        items_search = res_search.json()["results"]
        assert len(items_search) == 1
        assert items_search[0]["name"] == "Lipid Profile"

    def test_create_test_success(self, client, auth_headers):
        payload = {
            "name": "Vitamin D 25-Hydroxy",
            "category": "Biochemistry",
            "description": "Tests Vitamin D levels",
            "sample_type": "Blood",
        }
        response = client.post("/api/v1/tests", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Vitamin D 25-Hydroxy"
        assert data["category"] == "Biochemistry"

    def test_create_duplicate_test_name(self, client, auth_headers, test_diagnostic_test):
        payload = {
            "name": test_diagnostic_test.name,
            "category": "Pathology",
            "sample_type": "Blood",
        }
        response = client.post("/api/v1/tests", json=payload, headers=auth_headers)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()


class TestCentreOfferings:
    """Tests for /api/v1/centres/{centre_id}/tests endpoints."""

    def test_get_centre_tests(self, client, test_centre_test, test_centre):
        response = client.get(f"/api/v1/centres/{test_centre.id}/tests")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["centre_id"] == str(test_centre.id)
        assert float(data[0]["price"]) == float(test_centre_test.price)

    def test_add_test_to_centre_success(self, client, auth_headers, test_centre, db):
        new_test = DiagnosticTest(
            name="Hemoglobin A1c (HbA1c)",
            category="Diabetes",
            description="Glycated hemoglobin test",
            sample_type="Blood",
        )
        db.add(new_test)
        db.commit()
        db.refresh(new_test)

        payload = {
            "test_id": str(new_test.id),
            "price": 550.00,
            "is_available": True,
        }
        response = client.post(
            f"/api/v1/centres/{test_centre.id}/tests",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["centre_id"] == str(test_centre.id)
        assert data["test_id"] == str(new_test.id)
        assert float(data["price"]) == 550.00

    def test_add_test_invalid_price(self, client, auth_headers, test_centre, test_diagnostic_test):
        payload = {
            "test_id": str(test_diagnostic_test.id),
            "price": -50.00,
            "is_available": True,
        }
        response = client.post(
            f"/api/v1/centres/{test_centre.id}/tests",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 422  # Pydantic validator gt=0
