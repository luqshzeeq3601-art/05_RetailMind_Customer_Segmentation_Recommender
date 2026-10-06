"""Unit and integration tests for RetailMind FastAPI microservice."""

from fastapi.testclient import TestClient

from retailmind.api import app

client = TestClient(app)


def test_api_health_endpoint():
    """Verify /health returns 200 with valid metadata."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.2.0"
    assert data["catalog_size"] > 0
    assert data["active_customers"] > 0


def test_api_recommend_known_customer():
    """Verify POST /recommend returns personalized recommendations for known customer."""
    payload = {
        "customer_id": "17850",
        "top_k": 5,
        "mode": "repeat_allowed",
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "17850"
    assert data["returned_k"] == 5
    assert len(data["items"]) == 5
    assert data["items"][0]["rank"] == 1
    assert "stock_code" in data["items"][0]
    assert "reason_code" in data["items"][0]


def test_api_recommend_unknown_customer():
    """Verify POST /recommend safely falls back to global popularity for unknown customer."""
    payload = {
        "customer_id": "UNKNOWN-9999",
        "top_k": 5,
        "mode": "repeat_allowed",
    }
    response = client.post("/recommend", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_id"] == "UNKNOWN-9999"
    assert data["customer_status"] == "unknown_customer"
    assert data["returned_k"] == 5
    assert all(item["is_fallback"] for item in data["items"])


def test_api_segments_endpoint():
    """Verify GET /segments returns all three customer segments."""
    response = client.get("/segments")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    segment_ids = {seg["segment_id"] for seg in data}
    assert "SG01" in segment_ids
    assert "SG02" in segment_ids
    assert "SG03" in segment_ids


def test_api_customer_profile():
    """Verify GET /customer/{id}/profile returns profile for known and unknown customers."""
    # Known customer
    resp_known = client.get("/customer/17850/profile")
    assert resp_known.status_code == 200
    data_k = resp_known.json()
    assert data_k["customer_id"] == "17850"
    assert data_k["status"] in ["known_active", "known_inactive"]
    assert data_k["segment_id"] is not None

    # Unknown customer
    resp_un = client.get("/customer/UNKNOWN-0000/profile")
    assert resp_un.status_code == 200
    data_u = resp_un.json()
    assert data_u["customer_id"] == "UNKNOWN-0000"
    assert data_u["status"] == "unknown_customer"
    assert data_u["segment_id"] is None
