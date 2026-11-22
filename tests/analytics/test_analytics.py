"""
M4 Analytics Engine Integration and Access Control Tests.

Validates:
- Manager Dashboard response structure and keys (ahs, rs)
- All 108 assets represented
- Correct ranking order (AHS descending, RS descending)
- Latest score per asset retrieval
- Role-based access control per Detailed Design Chapter 5 Section 5.2
"""

from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from backend.app.database.database import SessionLocal
from backend.app.main import app
from backend.app.models.maintenance import AssetHealthScore, RiskScore


@pytest.fixture(scope="module")
def client():
    """Module-level FastAPI test client."""
    with TestClient(app) as test_client:
        yield test_client


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


# ----------------------------------------------------------------------
# Dashboard Contract & Data Tests
# ----------------------------------------------------------------------


def test_analytics_dashboard_structure(client, manager_headers):
    """Dashboard returns 200 and matches expected keys and item shapes."""
    resp = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "ahs" in data
    assert "rs" in data
    assert isinstance(data["ahs"], list)
    assert isinstance(data["rs"], list)

    for item in data["ahs"]:
        assert "asset_id" in item
        assert "score" in item
        assert isinstance(item["asset_id"], int)
        assert isinstance(item["score"], (int, float))

    for item in data["rs"]:
        assert "asset_id" in item
        assert "score" in item
        assert isinstance(item["asset_id"], int)
        assert isinstance(item["score"], (int, float))


def test_analytics_dashboard_all_assets_represented(client, manager_headers):
    """All 108 assets are represented in both ahs and rs with no duplicates."""
    resp = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()

    ahs_ids = [item["asset_id"] for item in data["ahs"]]
    rs_ids = [item["asset_id"] for item in data["rs"]]

    assert len(ahs_ids) == 108
    assert len(set(ahs_ids)) == 108

    assert len(rs_ids) == 108
    assert len(set(rs_ids)) == 108


def test_analytics_dashboard_ranking_order(client, manager_headers):
    """AHS is sorted descending (healthiest first) and RS is sorted descending (highest risk first)."""
    resp = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
    assert resp.status_code == 200
    data = resp.json()

    ahs_scores = [item["score"] for item in data["ahs"]]
    for i in range(len(ahs_scores) - 1):
        assert ahs_scores[i] >= ahs_scores[i + 1], f"AHS not descending at index {i}: {ahs_scores[i]} < {ahs_scores[i+1]}"

    rs_scores = [item["score"] for item in data["rs"]]
    for i in range(len(rs_scores) - 1):
        assert rs_scores[i] >= rs_scores[i + 1], f"RS not descending at index {i}: {rs_scores[i]} < {rs_scores[i+1]}"


def test_analytics_dashboard_latest_score_per_asset(client, manager_headers):
    """Latest scores use assessment time, then record ID as a tie-breaker."""
    db = SessionLocal()
    test_records = []
    try:
        base_time = datetime.now()

        # Asset 1: newer timestamps win even when their IDs are lower.
        newer_ahs = AssetHealthScore(
            asset_id=1,
            score=11.11,
            assessment_timestamp=base_time + timedelta(days=2),
            explanation="Newer timestamp with lower AHS ID.",
        )
        older_ahs = AssetHealthScore(
            asset_id=1,
            score=22.22,
            assessment_timestamp=base_time + timedelta(days=1),
            explanation="Older timestamp with higher AHS ID.",
        )
        newer_rs = RiskScore(
            asset_id=1,
            score=31.11,
            assessment_timestamp=base_time + timedelta(days=2),
            explanation="Newer timestamp with lower RS ID.",
        )
        older_rs = RiskScore(
            asset_id=1,
            score=42.22,
            assessment_timestamp=base_time + timedelta(days=1),
            explanation="Older timestamp with higher RS ID.",
        )

        # Asset 2: equal timestamps use the higher record ID.
        tie_timestamp = base_time + timedelta(days=3)
        first_ahs = AssetHealthScore(
            asset_id=2,
            score=51.11,
            assessment_timestamp=tie_timestamp,
            explanation="Earlier AHS ID at equal timestamp.",
        )
        latest_ahs = AssetHealthScore(
            asset_id=2,
            score=62.22,
            assessment_timestamp=tie_timestamp,
            explanation="Higher AHS ID at equal timestamp.",
        )
        first_rs = RiskScore(
            asset_id=2,
            score=71.11,
            assessment_timestamp=tie_timestamp,
            explanation="Earlier RS ID at equal timestamp.",
        )
        latest_rs = RiskScore(
            asset_id=2,
            score=82.22,
            assessment_timestamp=tie_timestamp,
            explanation="Higher RS ID at equal timestamp.",
        )
        test_records = [
            newer_ahs,
            older_ahs,
            newer_rs,
            older_rs,
            first_ahs,
            latest_ahs,
            first_rs,
            latest_rs,
        ]
        db.add_all(test_records)
        db.commit()

        assert newer_ahs.ahs_id < older_ahs.ahs_id
        assert newer_rs.risk_score_id < older_rs.risk_score_id
        assert first_ahs.ahs_id < latest_ahs.ahs_id
        assert first_rs.risk_score_id < latest_rs.risk_score_id

        resp = client.get("/api/v1/analytics/dashboard", headers=manager_headers)
        assert resp.status_code == 200
        data = resp.json()

        ahs_scores = {item["asset_id"]: item["score"] for item in data["ahs"]}
        rs_scores = {item["asset_id"]: item["score"] for item in data["rs"]}

        assert ahs_scores[1] == 11.11
        assert rs_scores[1] == 31.11
        assert ahs_scores[2] == 62.22
        assert rs_scores[2] == 82.22
    finally:
        if test_records:
            for record in test_records:
                db.delete(record)
            db.commit()
        db.close()


# ----------------------------------------------------------------------
# Role-Based Access Control Tests
# ----------------------------------------------------------------------


def test_analytics_dashboard_role_access(
    client, engineer_headers, maintenance_headers, manager_headers, admin_headers, inspector_headers
):
    """GET /api/v1/analytics/dashboard:
    Allowed: Engineer, Maintenance Officer, Utility Manager (200).
    Denied: Administrator, Field Inspector (403).
    Unauthenticated: 401.
    """
    # Allowed roles
    assert client.get("/api/v1/analytics/dashboard", headers=engineer_headers).status_code == 200
    assert client.get("/api/v1/analytics/dashboard", headers=maintenance_headers).status_code == 200
    assert client.get("/api/v1/analytics/dashboard", headers=manager_headers).status_code == 200

    # Denied roles
    assert client.get("/api/v1/analytics/dashboard", headers=admin_headers).status_code == 403
    assert client.get("/api/v1/analytics/dashboard", headers=inspector_headers).status_code == 403

    # Unauthenticated
    assert client.get("/api/v1/analytics/dashboard").status_code == 401

def test_analytics_process_role_access(
    client,
    engineer_headers,
    maintenance_headers,
    manager_headers,
    admin_headers,
    inspector_headers,
    monkeypatch,
):
    """Verify role permissions without executing or committing analytics."""

    calls = []

    def fake_run_analytics_for_all(db):
        calls.append(db)
        return {
            "total_anomalies": 0,
            "assets_processed": 0,
            "asset_decisions": [],
            "maintenance_queue": [],
        }

    monkeypatch.setattr(
        "backend.app.routes.analytics.run_analytics_for_all",
        fake_run_analytics_for_all,
    )

    # Engineer is allowed. The analytics service is mocked.
    resp = client.post(
        "/api/v1/analytics/process",
        headers=engineer_headers,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["assets_processed"] == 0
    assert body["total_anomalies"] == 0
    assert body["asset_decisions"] == []
    assert body["maintenance_queue"] == []
    assert len(calls) == 1

    # Other authority roles are denied.
    assert client.post(
        "/api/v1/analytics/process",
        headers=maintenance_headers,
    ).status_code == 403

    assert client.post(
        "/api/v1/analytics/process",
        headers=manager_headers,
    ).status_code == 403

    assert client.post(
        "/api/v1/analytics/process",
        headers=admin_headers,
    ).status_code == 403

    assert client.post(
        "/api/v1/analytics/process",
        headers=inspector_headers,
    ).status_code == 403

    # Unauthenticated request is denied.
    assert client.post(
        "/api/v1/analytics/process",
    ).status_code == 401

    # Only the authorized Engineer request reached the mocked service.
    assert len(calls) == 1
