"""
Tests for authority user management endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.database.connection import SessionLocal
from backend.app.main import app
from backend.app.models.user import User

SEEDED_EMAILS = {
    "admin@aquashield.demo",
    "engineer@aquashield.demo",
    "maintenance@aquashield.demo",
    "inspector@aquashield.demo",
    "manager@aquashield.demo",
}


@pytest.fixture(scope="module")
def client():
    """Module-level FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True, scope="module")
def clean_test_users():
    """Ensure non-seeded test users are cleaned up before and after module runs."""
    db = SessionLocal()
    try:
        db.query(User).filter(~User.email.in_(SEEDED_EMAILS)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(User).filter(~User.email.in_(SEEDED_EMAILS)).delete(synchronize_session=False)
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def admin_headers(client):
    """Authorization headers for Administrator."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def engineer_headers(client):
    """Authorization headers for Engineer."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "engineer@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def managed_user(client, admin_headers):
    """Create a persistent user for update and retrieval tests."""
    resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Managed Test User",
            "email": "managed.user@aquashield.demo",
            "password": "initialpassword123",
            "role": "Field Inspector",
        },
    )
    assert resp.status_code == 201
    return resp.json()


def test_create_user_admin(client, admin_headers):
    """Admin creates a new user; response contains user_id and excludes password_hash."""
    resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Created Worker",
            "email": "worker.create@aquashield.demo",
            "password": "securepassword123",
            "role": "Maintenance Officer",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "user_id" in data
    assert data["name"] == "Created Worker"
    assert data["email"] == "worker.create@aquashield.demo"
    assert data["role"] == "Maintenance Officer"
    assert "created_at" in data
    assert "password_hash" not in data


def test_create_user_duplicate_email(client, admin_headers):
    """Creating a user with an existing email returns 409 conflict."""
    resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Duplicate Admin",
            "email": "admin@aquashield.demo",
            "password": "password12345",
            "role": "Administrator",
        },
    )
    assert resp.status_code == 409
    data = resp.json()
    assert "detail" in data
    assert "password_hash" not in data


def test_create_user_invalid_role(client, admin_headers):
    """Creating a user with an invalid role returns 422 unprocessable entity."""
    resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Invalid Role",
            "email": "invalid.role@aquashield.demo",
            "password": "validpassword123",
            "role": "Boss",
        },
    )
    assert resp.status_code == 422
    assert "password_hash" not in resp.json()


def test_create_user_short_password(client, admin_headers):
    """Creating a user with password < 8 characters returns 422."""
    resp = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "name": "Short Pass",
            "email": "short.pass@aquashield.demo",
            "password": "abc",
            "role": "Field Inspector",
        },
    )
    assert resp.status_code == 422
    assert "password_hash" not in resp.json()


def test_list_users(client, admin_headers):
    """Admin lists all users; returns seeded users + created users without password_hash."""
    resp = client.get("/api/v1/users", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 5
    assert len(data["users"]) == data["total"]
    for user in data["users"]:
        assert "password_hash" not in user


def test_list_users_non_admin(client, engineer_headers):
    """Non-admin user receives 403 Forbidden when listing users."""
    resp = client.get("/api/v1/users", headers=engineer_headers)
    assert resp.status_code == 403
    assert "password_hash" not in resp.json()


def test_update_user_name(client, admin_headers, managed_user):
    """PATCH user name updates successfully and returns 200."""
    user_id = managed_user["user_id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"name": "New Name"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "New Name"
    assert "password_hash" not in data


def test_update_user_email(client, admin_headers, managed_user):
    """PATCH user email updates successfully and returns 200."""
    user_id = managed_user["user_id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"email": "new.email.updated@aquashield.demo"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "new.email.updated@aquashield.demo"
    assert "password_hash" not in data


def test_update_user_duplicate_email(client, admin_headers, managed_user):
    """PATCH user with an email already taken returns 409 Conflict."""
    user_id = managed_user["user_id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"email": "admin@aquashield.demo"},
    )
    assert resp.status_code == 409
    assert "password_hash" not in resp.json()


def test_update_user_unknown_field(client, admin_headers, managed_user):
    """PATCH user with unknown/forbidden fields like role returns 422."""
    user_id = managed_user["user_id"]
    resp = client.patch(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"role": "Engineer"},
    )
    assert resp.status_code == 422
    assert "password_hash" not in resp.json()


def test_update_user_unknown_id(client, admin_headers):
    """PATCH non-existent user returns 404 Not Found."""
    resp = client.patch(
        "/api/v1/users/999999",
        headers=admin_headers,
        json={"name": "Ghost User"},
    )
    assert resp.status_code == 404
    assert "password_hash" not in resp.json()


def test_get_user_by_id(client, admin_headers, managed_user):
    """GET user by user_id returns 200 with user profile excluding password_hash."""
    user_id = managed_user["user_id"]
    resp = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["user_id"] == user_id
    assert "password_hash" not in data


def test_get_user_not_found(client, admin_headers):
    """GET non-existent user returns 404 Not Found."""
    resp = client.get("/api/v1/users/999999", headers=admin_headers)
    assert resp.status_code == 404
    assert "password_hash" not in resp.json()
