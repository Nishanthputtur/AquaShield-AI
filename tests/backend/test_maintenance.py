"""
Tests for maintenance endpoints (Maintenance Officer creation and review).
"""

from datetime import datetime
import pytest
from fastapi.testclient import TestClient

from backend.app.database.connection import SessionLocal
from backend.app.main import app
from backend.app.models.asset import Asset
from backend.app.models.maintenance import MaintenanceRecord


@pytest.fixture(scope="module")
def client():
    """Module-level FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True, scope="module")
def clean_maintenance():
    """Clean up test maintenance records before and after module runs."""
    db = SessionLocal()
    try:
        db.query(MaintenanceRecord).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(MaintenanceRecord).delete()
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="module")
def mo_headers(client):
    """Authorization headers for Maintenance Officer (user_id 3)."""
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


def test_mo_creates_maintenance(client, mo_headers):
    """Maintenance Officer creates a maintenance record; maintenance_officer_id is server-derived from JWT."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=mo_headers,
        json={
            "asset_id": "C1-P-001",
            "maintenance_details": "Replaced worn gasket and tested pressure relief valve.",
            "status": "Completed",
            "notes": "Operation restored within nominal limits.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "maintenance_id" in data
    assert data["asset_id"] == "C1-P-001"
    assert data["maintenance_officer_id"] == 3
    assert data["maintenance_details"] == "Replaced worn gasket and tested pressure relief valve."
    assert data["status"] == "Completed"
    assert data["notes"] == "Operation restored within nominal limits."
    assert "maintenance_date" in data
    assert "password_hash" not in data


def test_mo_creates_maintenance_with_officer_id_in_body(client, mo_headers):
    """Supplying maintenance_officer_id in request body is rejected with 422 (strict schema)."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=mo_headers,
        json={
            "asset_id": "C1-P-001",
            "maintenance_details": "Test details.",
            "status": "Pending",
            "maintenance_officer_id": 999,
        },
    )
    assert resp.status_code == 422


def test_create_maintenance_referenced_asset_not_found(client, mo_headers):
    """Submitting maintenance for an unknown asset returns 404."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=mo_headers,
        json={
            "asset_id": "NONEXISTENT-ASSET-XYZ",
            "maintenance_details": "Maintenance of missing asset.",
            "status": "Scheduled",
        },
    )
    assert resp.status_code == 404


def test_admin_attempts_post_maintenance(client, admin_headers):
    """Administrator is denied maintenance creation per D04-11; returns 403."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=admin_headers,
        json={
            "asset_id": "C1-P-001",
            "maintenance_details": "Admin maintenance.",
            "status": "Scheduled",
        },
    )
    assert resp.status_code == 403


def test_engineer_attempts_post_maintenance(client, engineer_headers):
    """Engineer is denied maintenance creation; returns 403."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=engineer_headers,
        json={
            "asset_id": "C1-P-001",
            "maintenance_details": "Engineer maintenance.",
            "status": "Scheduled",
        },
    )
    assert resp.status_code == 403


def test_fi_attempts_post_maintenance(client, inspector_headers):
    """Field Inspector is denied maintenance creation; returns 403."""
    resp = client.post(
        "/api/v1/maintenance",
        headers=inspector_headers,
        json={
            "asset_id": "C1-P-001",
            "maintenance_details": "Field Inspector maintenance.",
            "status": "Scheduled",
        },
    )
    assert resp.status_code == 403


def test_mo_lists_maintenance(client, mo_headers):
    """Maintenance Officer retrieves maintenance records with embedded asset context."""
    resp = client.get("/api/v1/maintenance", headers=mo_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "maintenance_records" in data
    assert "total" in data
    assert data["total"] >= 1
    assert len(data["maintenance_records"]) == data["total"]

    first = data["maintenance_records"][0]
    assert "maintenance_id" in first
    assert "asset_id" in first
    assert "maintenance_officer_id" in first
    assert "asset" in first
    assert first["asset"]["name"] == "Pipeline C1-P-001"
    assert "password_hash" not in first["asset"]


def test_mo_sees_all_maintenance_records(client, mo_headers):
    """Maintenance Officer reads ALL maintenance records per D04-14 (not own-only)."""
    # Insert another maintenance record belonging to another user / officer (e.g. user_id 1)
    db = SessionLocal()
    try:
        pipeline = db.query(Asset).filter(Asset.asset_name == "C1-P-001").first()
        assert pipeline is not None
        foreign_record = MaintenanceRecord(
            asset_id=pipeline.asset_id,
            maintenance_officer_id=1,  # seeded user_id 1 (distinct from MO user_id 3)
            maintenance_date=datetime.now(),
            maintenance_details="Third-party contractor valve overhaul.",
            status="Completed",
            notes="Completed under external warranty.",
        )
        db.add(foreign_record)
        db.commit()
    finally:
        db.close()

    resp = client.get("/api/v1/maintenance", headers=mo_headers)
    assert resp.status_code == 200
    data = resp.json()
    officer_ids = {r["maintenance_officer_id"] for r in data["maintenance_records"]}
    assert 3 in officer_ids
    assert 1 in officer_ids
    assert data["total"] >= 2



def test_admin_attempts_get_maintenance(client, admin_headers):
    """Administrator is denied maintenance read per D04-11; returns 403."""
    resp = client.get("/api/v1/maintenance", headers=admin_headers)
    assert resp.status_code == 403


def test_fi_attempts_get_maintenance(client, inspector_headers):
    """Field Inspector is denied maintenance read; returns 403."""
    resp = client.get("/api/v1/maintenance", headers=inspector_headers)
    assert resp.status_code == 403


def test_engineer_attempts_get_maintenance(client, engineer_headers):
    """Engineer is denied maintenance read; returns 403."""
    resp = client.get("/api/v1/maintenance", headers=engineer_headers)
    assert resp.status_code == 403


def test_unauthenticated_maintenance(client):
    """Unauthenticated requests return 401."""
    assert client.post(
        "/api/v1/maintenance",
        json={"asset_id": "C1-P-001", "maintenance_details": "Test", "status": "Pending"},
    ).status_code == 401
    assert client.get("/api/v1/maintenance").status_code == 401
