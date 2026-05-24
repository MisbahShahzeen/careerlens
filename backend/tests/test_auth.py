from fastapi.testclient import TestClient
from app.main import app
import uuid

client = TestClient(app)

def random_email():
    return f"test_{uuid.uuid4().hex[:8]}@example.com"

def test_register_new_user():
    email = random_email()
    response = client.post("/auth/register", json={
        "email": email,
        "password": "testpass123"
    })
    assert response.status_code == 201
    assert "user_id" in response.json()

def test_register_duplicate_email_fails():
    email = random_email()
    client.post("/auth/register", json={"email": email, "password": "pass1"})
    response = client.post("/auth/register", json={"email": email, "password": "pass2"})
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

def test_login_with_valid_credentials():
    email = random_email()
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    response = client.post("/auth/login", data={
        "username": email,
        "password": "testpass123"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()

def test_login_with_wrong_password_fails():
    email = random_email()
    client.post("/auth/register", json={"email": email, "password": "correctpass"})
    response = client.post("/auth/login", data={
        "username": email,
        "password": "wrongpass"
    })
    assert response.status_code == 401

def test_analyze_endpoint_requires_auth():
    response = client.post("/analysis/analyze")
    assert response.status_code == 401

def test_get_analysis_requires_auth():
    response = client.get("/analysis/1")
    assert response.status_code == 401

def test_get_nonexistent_analysis_returns_404():
    email = random_email()
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": "testpass123"
    })
    token = login_res.json()["access_token"]

    response = client.get(
        "/analysis/999999",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 404

def test_history_endpoint_returns_list():
    email = random_email()
    client.post("/auth/register", json={"email": email, "password": "testpass123"})
    login_res = client.post("/auth/login", data={
        "username": email,
        "password": "testpass123"
    })
    token = login_res.json()["access_token"]

    response = client.get(
        "/analysis/history",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)