from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_analyze_rag_requires_auth():
    # No token → should be rejected
    response = client.post("/analysis/analyze-rag")
    assert response.status_code == 401


def test_evidence_endpoint_requires_auth():
    response = client.get("/analysis/1/evidence")
    assert response.status_code == 401


def test_compare_requires_auth():
    response = client.post("/analysis/compare")
    assert response.status_code == 401


def test_evidence_404_for_missing_analysis():
    import uuid
    email = f"ragtest_{uuid.uuid4().hex[:8]}@example.com"
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    login = client.post("/auth/login", data={"username": email, "password": "testpass123"})
    token = login.json()["access_token"]

    # Request evidence for an analysis that doesn't exist
    response = client.get(
        "/analysis/999999/evidence",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404