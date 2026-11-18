"""
Authentication endpoint tests (Day 1 & Day 2 tests).
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import jwt
import pytest

from backend.app.config.settings import settings
from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """Module-level TestClient for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


def test_login_valid_credentials(client):
    """Test successful login returns 200 and access token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aquashield.demo", "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert len(data["access_token"]) > 0


def test_login_wrong_password(client):
    """Test login with wrong password returns 401 with generic error message."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aquashield.demo", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Invalid email or password"


def test_me_authenticated(client):
    """Test /me returns profile for authenticated user with valid token."""
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aquashield.demo", "password": "password123"},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "user_id" in data
    assert isinstance(data["user_id"], int)
    assert data["name"] == "Admin User"
    assert data["email"] == "admin@aquashield.demo"
    assert data["role"] == "Administrator"


def test_me_unauthenticated(client):
    """Test /me returns 401 when request has no authorization token."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.parametrize(
    "email",
    [
        "admin@aquashield.demo",
        "engineer@aquashield.demo",
        "maintenance@aquashield.demo",
        "inspector@aquashield.demo",
        "manager@aquashield.demo",
    ],
)
def test_login_all_five_roles(client, email):
    """Test all five seeded authority roles log in successfully with 200 and token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str) and len(data["access_token"]) > 0


def test_me_with_invalid_token(client):
    """Test /me returns 401 when provided an invalid/garbage token."""
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.garbage.token"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_me_with_expired_token(client):
    """Test /me returns 401 when provided an expired token."""
    now = datetime.now(timezone.utc)
    expired_payload = {
        "sub": "1",
        "role": "Administrator",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


def test_login_generic_error_message(client):
    """Unknown email and wrong password return identical 401 response bodies."""
    resp_unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "unknown@aquashield.demo", "password": "password123"},
    )
    resp_wrong_pw = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aquashield.demo", "password": "wrongpassword"},
    )
    assert resp_unknown.status_code == 401
    assert resp_wrong_pw.status_code == 401
    assert resp_unknown.json() == resp_wrong_pw.json()
    assert resp_unknown.json()["detail"] == "Invalid email or password"
