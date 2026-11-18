"""
Tests for inspection endpoints (Field Inspector submission, Maintenance Officer review).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.database.connection import SessionLocal
from backend.app.main import app
from backend.app.models.maintenance import Inspection


@pytest.fixture(scope="module")
def client():
    """Module-level FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True, scope="module")
def clean_inspections():
    """Clean up test inspections before and after module runs."""
    db = SessionLocal()
    try:
        db.query(Inspection).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Inspection).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def inspector_headers(client):
    """Authorization headers for Field Inspector (user_id 4)."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "inspector@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def mo_headers(client):
    """Authorization headers for Maintenance Officer."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "maintenance@aquashield.demo", "password": "password123"},
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
def engineer_headers(client):
    """Authorization headers for Engineer."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "engineer@aquashield.demo", "password": "password123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_fi_creates_inspection(client, inspector_headers):
    """Field Inspector creates an inspection; inspector_id is server-derived from JWT."""
    resp = client.post(
        "/api/v1/inspections",
        headers=inspector_headers,
        json={
            "asset_id": "C1-P-001",
            "findings": "Valve casing shows minor corrosion; operating smoothly.",
            "condition": "Fair",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "inspection_id" in data
    assert data["asset_id"] == "C1-P-001"
    assert data["inspector_id"] == 4
    assert data["findings"] == "Valve casing shows minor corrosion; operating smoothly."
    assert data["condition"] == "Fair"
    assert data["status"] == "recorded"
    assert "inspection_date" in data
    assert "password_hash" not in data


def test_fi_creates_inspection_with_inspector_id_in_body(client, inspector_headers):
    """Supplying inspector_id in request body is rejected with 422 (strict schema)."""
    resp = client.post(
        "/api/v1/inspections",
        headers=inspector_headers,
        json={
            "asset_id": "C1-P-001",
            "findings": "Test findings.",
            "inspector_id": 999,
        },
    )
    assert resp.status_code == 422


def test_create_inspection_referenced_asset_not_found(client, inspector_headers):
    """Submitting an inspection for an unknown asset returns 404."""
    resp = client.post(
        "/api/v1/inspections",
        headers=inspector_headers,
        json={
            "asset_id": "NONEXISTENT-ASSET-XYZ",
            "findings": "Inspection of missing asset.",
        },
    )
    assert resp.status_code == 404


def test_admin_attempts_post_inspections(client, admin_headers):
    """Administrator is denied inspection creation; returns 403."""
    resp = client.post(
        "/api/v1/inspections",
        headers=admin_headers,
        json={"asset_id": "C1-P-001", "findings": "Admin inspection."},
    )
    assert resp.status_code == 403


def test_engineer_attempts_post_inspections(client, engineer_headers):
    """Engineer is denied inspection creation; returns 403."""
    resp = client.post(
        "/api/v1/inspections",
        headers=engineer_headers,
        json={"asset_id": "C1-P-001", "findings": "Engineer inspection."},
    )
    assert resp.status_code == 403


def test_mo_attempts_post_inspections(client, mo_headers):
    """Maintenance Officer is denied inspection creation; returns 403."""
    resp = client.post(
        "/api/v1/inspections",
        headers=mo_headers,
        json={"asset_id": "C1-P-001", "findings": "MO inspection."},
    )
    assert resp.status_code == 403


def test_mo_lists_inspections(client, mo_headers):
    """Maintenance Officer retrieves inspection list with embedded asset context."""
    resp = client.get("/api/v1/inspections", headers=mo_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "inspections" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["inspections"]) == data["total"]

    first = data["inspections"][0]
    assert "inspection_id" in first
    assert "asset_id" in first
    assert "inspector_id" in first
    assert "asset" in first
    assert first["asset"]["name"] == "Pipeline C1-P-001"
    assert "password_hash" not in first["asset"]


def test_fi_attempts_get_inspections(client, inspector_headers):
    """Field Inspector is denied inspection history retrieval per D04-09; returns 403."""
    resp = client.get("/api/v1/inspections", headers=inspector_headers)
    assert resp.status_code == 403


def test_admin_attempts_get_inspections(client, admin_headers):
    """Administrator is denied inspection history retrieval per D04-08; returns 403."""
    resp = client.get("/api/v1/inspections", headers=admin_headers)
    assert resp.status_code == 403


def test_unauthenticated_inspections(client):
    """Unauthenticated requests return 401."""
    assert client.post("/api/v1/inspections", json={"asset_id": "C1-P-001", "findings": "Test"}).status_code == 401
    assert client.get("/api/v1/inspections").status_code == 401
