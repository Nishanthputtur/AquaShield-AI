"""
Tests for simulation control and monitoring readings endpoints.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.simulation_service import simulation_service


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
# Simulation endpoint tests
# ----------------------------------------------------------------------


def test_simulation_start_happy_path(client, engineer_headers):
    """Engineer starts simulation successfully returning RUNNING and tick 0."""
    asyncio.run(simulation_service._force_stopped())

    resp = client.post("/api/v1/simulation/start", headers=engineer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "RUNNING"
    assert data["tick"] == 0

    client.post("/api/v1/simulation/stop", headers=engineer_headers)


def test_simulation_pause_and_resume(client, engineer_headers):
    """Engineer pauses and resumes simulation successfully."""
    asyncio.run(simulation_service._force_stopped())
    client.post("/api/v1/simulation/start", headers=engineer_headers)

    pause_resp = client.post("/api/v1/simulation/pause", headers=engineer_headers)
    assert pause_resp.status_code == 200
    assert pause_resp.json()["state"] == "PAUSED"

    resume_resp = client.post("/api/v1/simulation/resume", headers=engineer_headers)
    assert resume_resp.status_code == 200
    assert resume_resp.json()["state"] == "RUNNING"

    client.post("/api/v1/simulation/stop", headers=engineer_headers)


def test_simulation_stop_and_reset(client, engineer_headers):
    """Engineer stops and resets simulation returning STOPPED and tick 0."""
    asyncio.run(simulation_service._force_stopped())
    client.post("/api/v1/simulation/start", headers=engineer_headers)

    stop_resp = client.post("/api/v1/simulation/stop", headers=engineer_headers)
    assert stop_resp.status_code == 200
    assert stop_resp.json()["state"] == "STOPPED"
    assert stop_resp.json()["tick"] == 0

    reset_resp = client.post("/api/v1/simulation/reset", headers=engineer_headers)
    assert reset_resp.status_code == 200
    assert reset_resp.json()["state"] == "STOPPED"
    assert reset_resp.json()["tick"] == 0


def test_simulation_state_get(client, engineer_headers):
    """Engineer retrieves simulation state successfully through approved schema."""
    asyncio.run(simulation_service._force_stopped())
    resp = client.get("/api/v1/simulation/state", headers=engineer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["state"] == "STOPPED"
    assert "tick" in data


def test_simulation_invalid_action(client, engineer_headers):
    """Actions outside the 5 approved actions (e.g. step) are rejected with 422."""
    step_resp = client.post("/api/v1/simulation/step", headers=engineer_headers)
    assert step_resp.status_code == 422

    invalid_resp = client.post("/api/v1/simulation/invalid", headers=engineer_headers)
    assert invalid_resp.status_code == 422


def test_simulation_unauthenticated(client):
    """Unauthenticated requests to simulation endpoints return 401."""
    assert client.post("/api/v1/simulation/start").status_code == 401
    assert client.get("/api/v1/simulation/state").status_code == 401


def test_simulation_wrong_role_admin(client, admin_headers):
    """Administrator is denied simulation access per D04-07 returning 403."""
    assert client.post("/api/v1/simulation/start", headers=admin_headers).status_code == 403
    assert client.get("/api/v1/simulation/state", headers=admin_headers).status_code == 403


def test_simulation_wrong_role_other(client, inspector_headers, maintenance_headers, manager_headers):
    """Non-Engineer roles are denied simulation access returning 403."""
    assert client.post("/api/v1/simulation/start", headers=inspector_headers).status_code == 403
    assert client.post("/api/v1/simulation/start", headers=maintenance_headers).status_code == 403
    assert client.post("/api/v1/simulation/start", headers=manager_headers).status_code == 403


def test_simulation_conflict_state(client, engineer_headers):
    """Invalid lifecycle transitions raise 409 Conflict."""
    asyncio.run(simulation_service._force_stopped())
    client.post("/api/v1/simulation/start", headers=engineer_headers)

    # Starting while RUNNING -> 409
    dup_start = client.post("/api/v1/simulation/start", headers=engineer_headers)
    assert dup_start.status_code == 409

    client.post("/api/v1/simulation/stop", headers=engineer_headers)

    # Pausing while STOPPED -> 409
    invalid_pause = client.post("/api/v1/simulation/pause", headers=engineer_headers)
    assert invalid_pause.status_code == 409


# ----------------------------------------------------------------------
# Monitoring endpoint tests
# ----------------------------------------------------------------------


def test_monitoring_readings_happy_path(client, engineer_headers):
    """Engineer retrieves sensor readings list successfully with 200."""
    resp = client.get("/api/v1/monitoring/readings", headers=engineer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "readings" in data
    assert isinstance(data["readings"], list)


def test_monitoring_readings_inline_asset_context(client, engineer_headers):
    """Readings returned to Engineer contain inline asset context per D04-06."""
    # Ensure readings exist by running one tick if needed
    from backend.app.database.connection import SessionLocal
    from backend.app.models.sensor import SensorReading
    from simulator.city.virtual_city import create_virtual_city
    from simulator.sensors import initialize_sensors

    create_virtual_city()
    initialize_sensors()

    db = SessionLocal()
    try:
        count = db.query(SensorReading).count()
        if count == 0:
            # Produce and persist one batch of readings
            from backend.app.services.monitoring_service import persist_readings
            from simulator.generators import SimulationGenerator
            gen = SimulationGenerator()
            gen.start()
            readings = gen.generate()
            persist_readings(db, readings)
            db.commit()
            gen.stop()
    finally:
        db.close()

    resp = client.get("/api/v1/monitoring/readings", headers=engineer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["readings"]) > 0

    first = data["readings"][0]
    assert "sensor_id" in first
    assert "asset_id" in first
    assert "parameter" in first
    assert "value" in first
    assert "unit" in first
    assert "timestamp" in first
    assert "asset" in first
    assert first["asset"] is not None

    asset = first["asset"]
    assert "asset_id" in asset
    assert "name" in asset
    assert "type" in asset
    assert "status" in asset
    assert "city_name" in asset
    assert "zone_name" in asset
    assert "password_hash" not in asset


def test_monitoring_readings_unauthenticated(client):
    """Unauthenticated request to monitoring readings returns 401."""
    resp = client.get("/api/v1/monitoring/readings")
    assert resp.status_code == 401


def test_monitoring_readings_limit_query_params(client, engineer_headers):
    """Test limit query parameter behavior for monitoring readings."""
    # Default limit returns up to 100
    resp = client.get("/api/v1/monitoring/readings", headers=engineer_headers)
    assert resp.status_code == 200
    assert len(resp.json()["readings"]) <= 100

    # Explicit limit within bounds
    resp = client.get("/api/v1/monitoring/readings?limit=328", headers=engineer_headers)
    assert resp.status_code == 200
    assert len(resp.json()["readings"]) <= 328

    # Limit exceeds maximum (1000) -> 422
    resp = client.get("/api/v1/monitoring/readings?limit=5000", headers=engineer_headers)
    assert resp.status_code == 422

    # Limit below minimum (1) -> 422
    resp = client.get("/api/v1/monitoring/readings?limit=0", headers=engineer_headers)
    assert resp.status_code == 422


def test_monitoring_readings_wrong_role(
    client, admin_headers, inspector_headers, maintenance_headers, manager_headers
):
    """Non-Engineer authority roles are denied monitoring access with 403."""
    assert client.get("/api/v1/monitoring/readings", headers=admin_headers).status_code == 403
    assert client.get("/api/v1/monitoring/readings", headers=inspector_headers).status_code == 403
    assert client.get("/api/v1/monitoring/readings", headers=maintenance_headers).status_code == 403
    assert client.get("/api/v1/monitoring/readings", headers=manager_headers).status_code == 403

