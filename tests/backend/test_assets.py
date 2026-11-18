"""
Tests for asset lookup endpoint (Field Inspector only).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture(scope="module")
def client():
    """Module-level FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def inspector_headers(client):
    """Authorization headers for Field Inspector."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@aquashield.demo", "password": "password123"},
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
def maintenance_headers(client):
    """Authorization headers for Maintenance Officer."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "maintenance@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def manager_headers(client):
    """Authorization headers for Utility Manager."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "manager@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_asset_happy_path(client, inspector_headers):
    """Field Inspector retrieves asset by id successfully with exact 6 CONTRACT.md fields."""
    resp = client.get("/api/v1/assets/C1-P-001", headers=inspector_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["asset_id"] == "C1-P-001"
    assert "name" in data
    assert "type" in data
    assert "status" in data
    assert "city_name" in data
    assert "zone_name" in data
    assert len(data) == 6
    assert "password_hash" not in data


def test_get_asset_by_numeric_id(client, inspector_headers):
    """Field Inspector can also retrieve asset by database numeric id."""
    resp = client.get("/api/v1/assets/1", headers=inspector_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "asset_id" in data
    assert "name" in data
    assert "type" in data
    assert len(data) == 6


def test_get_asset_unknown_id(client, inspector_headers):
    """Non-existent asset ID returns contract-approved 404 with 'Resource not found'."""
    resp = client.get("/api/v1/assets/NONEXISTENT-ASSET-XYZ", headers=inspector_headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Resource not found"


def test_get_asset_unauthenticated(client):
    """Unauthenticated request to asset lookup returns 401."""
    resp = client.get("/api/v1/assets/C1-P-001")
    assert resp.status_code == 401


def test_get_asset_wrong_role_engineer(client, engineer_headers):
    """Engineer is denied standalone asset lookup per D04-06/CONTRACT.md; returns 403."""
    resp = client.get("/api/v1/assets/C1-P-001", headers=engineer_headers)
    assert resp.status_code == 403


def test_get_asset_wrong_role_admin(client, admin_headers):
    """Administrator is denied asset lookup; returns 403."""
    resp = client.get("/api/v1/assets/C1-P-001", headers=admin_headers)
    assert resp.status_code == 403


def test_get_asset_wrong_role_maintenance(client, maintenance_headers):
    """Maintenance Officer is denied asset lookup; returns 403."""
    resp = client.get("/api/v1/assets/C1-P-001", headers=maintenance_headers)
    assert resp.status_code == 403


def test_get_asset_wrong_role_manager(client, manager_headers):
    """Utility Manager is denied asset lookup; returns 403."""
    resp = client.get("/api/v1/assets/C1-P-001", headers=manager_headers)
    assert resp.status_code == 403


def test_get_asset_no_list_endpoint(client, inspector_headers):
    """No asset list endpoint exists per D04-05; /api/v1/assets returns 404 or 405."""
    resp = client.get("/api/v1/assets", headers=inspector_headers)
    assert resp.status_code in (404, 405)
