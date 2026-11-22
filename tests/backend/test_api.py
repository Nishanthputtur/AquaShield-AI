"""
Public Portal API test suite for AquaShield AI (M5).

Validates:
- Unauthenticated public access for all public endpoints.
- City and zone discovery.
- Area-specific water supply status.
- Area-specific operational issues & anomalies.
- Area-specific maintenance information (sanitized).
- Area-specific infrastructure breakdown.
- Water quality evaluation based on pH (approved thresholds 6.5 - 8.5).
- Public announcements and notifications.
- Complaint submission with and without zone.
- Complaint validation (short details, invalid zone).
- Complaint tracking by valid and invalid tracking IDs.
- Unpredictable unique tracking ID generation.
"""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from backend.app.database.database import SessionLocal
from backend.app.main import app
from backend.app.models.asset import Asset
from backend.app.models.city import City
from backend.app.models.maintenance import MaintenanceRecord
from backend.app.models.sensor import Anomaly, Sensor, SensorReading
from backend.app.models.user import User
from backend.app.models.zone import Zone
from backend.app.services.complaint_service import DEFAULT_PUBLIC_ANNOUNCEMENTS


@pytest.fixture(scope="module")
def client():
    """Module-level TestClient for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


def test_unauthenticated_public_access(client):
    """Confirm all public endpoints succeed without any authorization credentials."""
    public_endpoints = [
        "/api/v1/public/cities",
        "/api/v1/public/zones",
        "/api/v1/public/status",
        "/api/v1/public/water-quality",
        "/api/v1/public/issues",
        "/api/v1/public/maintenance",
        "/api/v1/public/infrastructure",
        "/api/v1/public/notifications",
    ]
    for endpoint in public_endpoints:
        res = client.get(endpoint)
        assert res.status_code == 200, f"Expected 200 for {endpoint}, got {res.status_code}"


def test_get_public_cities(client):
    """Retrieve all simulated cities with their operational zones."""
    res = client.get("/api/v1/public/cities")
    assert res.status_code == 200
    cities = res.json()
    assert len(cities) == 4
    city_names = {c["city_name"] for c in cities}
    assert "Zorawarpur" in city_names
    # Verify nested zones
    for city in cities:
        assert len(city["zones"]) == 4
        assert "city_id" in city


def test_get_public_zones(client):
    """Retrieve operational zones list with backward compatibility and filtering."""
    # All zones
    res = client.get("/api/v1/public/zones")
    assert res.status_code == 200
    zones = res.json()
    assert len(zones) == 16
    assert "zone_id" in zones[0]
    assert "name" in zones[0]  # Backward compatibility for existing public frontend

    # Filtered by city_id
    res_filtered = client.get("/api/v1/public/zones?city_id=1")
    assert res_filtered.status_code == 200
    filtered_zones = res_filtered.json()
    assert len(filtered_zones) == 4
    for z in filtered_zones:
        assert z["city_id"] == 1


def test_area_supply_status_overall_and_scoped(client):
    """Retrieve area-specific water supply status."""
    # Overall
    res = client.get("/api/v1/public/status")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "message" in data
    assert data["total_assets"] == 108
    assert data["operational_assets"] <= 108
    assert "last_updated" in data

    # Scoped to City 1
    res_city = client.get("/api/v1/public/status?city_id=1")
    assert res_city.status_code == 200
    city_data = res_city.json()
    assert "Zorawarpur" in city_data["area_name"]
    assert city_data["total_assets"] > 0
    assert city_data["total_assets"] < 108
    assert city_data["city_id"] == 1
    assert city_data["zone_id"] is None

    # Scoped to Zone 1
    res_zone = client.get("/api/v1/public/status?zone_id=1")
    assert res_zone.status_code == 200
    zone_data = res_zone.json()
    assert zone_data["total_assets"] > 0
    assert zone_data["total_assets"] < city_data["total_assets"]
    assert zone_data["city_id"] is None
    assert zone_data["zone_id"] == 1


def test_area_supply_status_rejects_invalid_or_mismatched_areas(client):
    """Status filters validate city and zone IDs before querying assets."""
    assert client.get(
        "/api/v1/public/status?city_id=999999"
    ).status_code == 404
    assert client.get(
        "/api/v1/public/status?zone_id=999999"
    ).status_code == 404

    cities = client.get("/api/v1/public/cities").json()
    first_city = cities[0]
    other_city = cities[1]
    other_zone_id = other_city["zones"][0]["zone_id"]
    response = client.get(
        f"/api/v1/public/status?city_id={first_city['city_id']}"
        f"&zone_id={other_zone_id}"
    )

    assert response.status_code == 404

@pytest.mark.parametrize(
    "endpoint,items_key",
    [
        ("/api/v1/public/issues", None),
        ("/api/v1/public/maintenance", None),
        ("/api/v1/public/infrastructure", "assets"),
    ],
)
def test_public_area_endpoints_validate_city_zone_filters(
    client, endpoint, items_key
):
    """All public area endpoints validate and apply city-zone filters."""

    cities = client.get("/api/v1/public/cities").json()
    city_a, city_b = cities[0], cities[1]
    zone_a = city_a["zones"][0]
    zone_b = city_b["zones"][0]

    # Invalid city ID
    response = client.get(
        endpoint, params={"city_id": 999999}
    )
    assert response.status_code == 404

    # Invalid zone ID
    response = client.get(
        endpoint, params={"zone_id": 999999}
    )
    assert response.status_code == 404

    # Zone does not belong to the supplied city
    response = client.get(
        endpoint,
        params={
            "city_id": city_a["city_id"],
            "zone_id": zone_b["zone_id"],
        },
    )
    assert response.status_code == 404

    # Test valid city, zone, matching city-zone, and unfiltered requests
    valid_filters = [
        {"city_id": city_a["city_id"]},
        {"zone_id": zone_a["zone_id"]},
        {
            "city_id": city_a["city_id"],
            "zone_id": zone_a["zone_id"],
        },
        {},
    ]

    for filters in valid_filters:
        response = client.get(endpoint, params=filters)
        assert response.status_code == 200

        data = response.json()
        items = data[items_key] if items_key else data

        if "city_id" in filters:
            assert all(
                item["city_name"] == city_a["city_name"]
                for item in items
            )

        if "zone_id" in filters:
            assert all(
                item["zone_name"] == zone_a["name"]
                for item in items
            )

        if items_key == "assets":
            assert data["total_count"] > 0

        if not filters and endpoint == "/api/v1/public/infrastructure":
            assert data["total_count"] == 108

def test_water_quality_ph_approved_thresholds(client):
    """Verify pH water quality evaluation against approved project thresholds (6.5 - 8.5)."""
    res = client.get("/api/v1/public/water-quality")
    assert res.status_code == 200
    data = res.json()
    assert data["parameter"] == "pH"
    assert data["unit"] == "pH"
    assert data["threshold_min"] == 6.5
    assert data["threshold_max"] == 8.5
    assert isinstance(data["ph_value"], (int, float))
    assert isinstance(data["is_safe"], bool)

    # Check logic matches approved thresholds
    if 6.5 <= data["ph_value"] <= 8.5:
        assert data["status"] == "Normal"
        assert data["is_safe"] is True
        assert "configured project reference range" in data["message"].lower()
        assert "does not assess overall drinking-water safety" in data["message"].lower()
    elif data["ph_value"] < 6.5:
        assert data["status"] == "Acidic Warning"
        assert data["is_safe"] is False
    else:
        assert data["status"] == "Alkaline Warning"
        assert data["is_safe"] is False


def test_water_quality_ph_scoped_to_zone(client):
    """Verify zone-specific water quality sampling."""
    res = client.get("/api/v1/public/water-quality?zone_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["ph_value"] > 0
    assert data["sample_asset"] is not None


def test_area_issues_retrieval(client):
    """Retrieve area-specific issues and operational anomalies."""
    res = client.get("/api/v1/public/issues?city_id=1")
    assert res.status_code == 200
    issues = res.json()
    assert isinstance(issues, list)
    for issue in issues:
        assert "anomaly_id" in issue
        assert "asset_name" in issue
        assert "anomaly_type" in issue


def test_area_issues_exclude_inactive_anomaly_statuses(client):
    """Public issues contain only detected, active, and open anomalies."""
    db = SessionLocal()
    records = []
    try:
        now = datetime.now()
        for anomaly_status in (
            "Detected",
            "Active",
            "Open",
            "resolved",
            "closed",
            "completed",
        ):
            anomaly = Anomaly(
                asset_id=1,
                sensor_reading_id=None,
                anomaly_type=f"Public Status Test {anomaly_status}",
                description="Temporary public issue status test.",
                detected_at=now,
                status=anomaly_status,
            )
            db.add(anomaly)
            records.append(anomaly)
        db.commit()

        response = client.get("/api/v1/public/issues?city_id=1")
        assert response.status_code == 200
        returned_ids = {item["anomaly_id"] for item in response.json()}

        assert {record.anomaly_id for record in records[:3]} <= returned_ids
        assert not ({record.anomaly_id for record in records[3:]} & returned_ids)
    finally:
        for record in records:
            db.delete(record)
        db.commit()
        db.close()


def test_area_maintenance_retrieval(client):
    """Retrieve sanitized area-specific maintenance notices."""
    res = client.get("/api/v1/public/maintenance")
    assert res.status_code == 200
    records = res.json()
    assert isinstance(records, list)
    for rec in records:
        assert "maintenance_id" in rec
        assert "asset_name" in rec
        assert "maintenance_details" in rec
        assert "status" in rec
        # Ensure no private officer identifiers leaked
        assert "maintenance_officer_id" not in rec
        assert "officer" not in rec


def test_area_maintenance_includes_only_scheduled_and_ongoing(client):
    """Public maintenance excludes completed activities and internal IDs."""
    db = SessionLocal()
    records = []
    try:
        officer = (
            db.query(User)
            .filter(User.role == "Maintenance Officer")
            .first()
        )
        assert officer is not None

        now = datetime.now()
        for maintenance_status in ("Scheduled", "In Progress", "Completed"):
            record = MaintenanceRecord(
                asset_id=1,
                maintenance_officer_id=officer.user_id,
                maintenance_date=now,
                maintenance_details=f"Temporary {maintenance_status} public test.",
                status=maintenance_status,
            )
            db.add(record)
            records.append(record)
        db.commit()

        response = client.get("/api/v1/public/maintenance?city_id=1")
        assert response.status_code == 200
        returned_records = {
            item["maintenance_id"]: item
            for item in response.json()
        }

        assert records[0].maintenance_id in returned_records
        assert records[1].maintenance_id in returned_records
        assert records[2].maintenance_id not in returned_records
        assert all(
            item["status"] in {"Scheduled", "In Progress"}
            for item in returned_records.values()
        )
        assert all(
            "maintenance_officer_id" not in item
            for item in returned_records.values()
        )
    finally:
        for record in records:
            db.delete(record)
        db.commit()
        db.close()


def test_water_quality_equal_timestamps_use_higher_reading_id(client):
    """pH selection breaks timestamp ties with the higher reading ID."""
    db = SessionLocal()
    readings = []
    try:
        sensor = (
            db.query(Sensor)
            .join(Asset, Sensor.asset_id == Asset.asset_id)
            .join(Zone, Asset.zone_id == Zone.zone_id)
            .filter(Sensor.sensor_type == "pH", Zone.city_id == 1)
            .first()
        )
        assert sensor is not None

        timestamp = datetime.now() + timedelta(days=10)
        first_reading = SensorReading(
            sensor_id=sensor.sensor_id,
            reading_value_numeric=6.61,
            reading_value_text=None,
            timestamp=timestamp,
            status="Normal",
        )
        latest_reading = SensorReading(
            sensor_id=sensor.sensor_id,
            reading_value_numeric=7.72,
            reading_value_text=None,
            timestamp=timestamp,
            status="Normal",
        )
        readings = [first_reading, latest_reading]
        db.add_all(readings)
        db.commit()

        assert first_reading.reading_id < latest_reading.reading_id
        response = client.get("/api/v1/public/water-quality?city_id=1")

        assert response.status_code == 200
        assert response.json()["ph_value"] == 7.72
    finally:
        for reading in readings:
            db.delete(reading)
        db.commit()
        db.close()


def test_water_quality_zone_without_sensor_uses_parent_city(client):
    """A zone without a direct pH sensor uses the latest city pH reading."""
    db = SessionLocal()
    reading = None
    try:
        target_zone = None
        city_sensor = None
        for candidate in db.query(Zone).order_by(Zone.zone_id.asc()).all():
            direct_sensor = (
                db.query(Sensor)
                .join(Asset, Sensor.asset_id == Asset.asset_id)
                .filter(
                    Sensor.sensor_type == "pH",
                    Asset.zone_id == candidate.zone_id,
                )
                .first()
            )
            if direct_sensor is None:
                city_sensor = (
                    db.query(Sensor)
                    .join(Asset, Sensor.asset_id == Asset.asset_id)
                    .join(Zone, Asset.zone_id == Zone.zone_id)
                    .filter(
                        Sensor.sensor_type == "pH",
                        Zone.city_id == candidate.city_id,
                    )
                    .first()
                )
                if city_sensor is not None:
                    target_zone = candidate
                    break

        assert target_zone is not None
        reading = SensorReading(
            sensor_id=city_sensor.sensor_id,
            reading_value_numeric=7.31,
            reading_value_text=None,
            timestamp=datetime.now() + timedelta(days=11),
            status="Normal",
        )
        db.add(reading)
        db.commit()

        response = client.get(
            f"/api/v1/public/water-quality?zone_id={target_zone.zone_id}"
        )

        assert response.status_code == 200
        assert response.json()["ph_value"] == 7.31
    finally:
        if reading is not None:
            db.delete(reading)
            db.commit()
        db.close()


def test_water_quality_invalid_area_ids_do_not_fall_back_to_network(client):
    """Invalid city and zone IDs return 404 rather than global pH data."""
    assert client.get(
        "/api/v1/public/water-quality?city_id=999999"
    ).status_code == 404
    assert client.get(
        "/api/v1/public/water-quality?zone_id=999999"
    ).status_code == 404


def test_water_quality_missing_readings_return_not_found(client):
    """A valid area with no numeric pH reading never receives a fake value."""
    db = SessionLocal()
    city = zone = asset = sensor = None
    try:
        suffix = datetime.now().strftime("%Y%m%d%H%M%S%f")
        city = City(city_name=f"No Reading City {suffix}")
        db.add(city)
        db.flush()
        zone = Zone(zone_name=f"No Reading Zone {suffix}", city_id=city.city_id)
        db.add(zone)
        db.flush()
        asset = Asset(
            zone_id=zone.zone_id,
            asset_name=f"No Reading Facility {suffix}",
            asset_type="TreatmentFacility",
            status="Operational",
            updated_at=datetime.now(),
        )
        db.add(asset)
        db.flush()
        sensor = Sensor(
            asset_id=asset.asset_id,
            sensor_type="pH",
            sensor_name=f"NO-READING-PH-{suffix}",
            status="Active",
        )
        db.add(sensor)
        db.commit()

        response = client.get(
            f"/api/v1/public/water-quality?city_id={city.city_id}"
        )

        assert response.status_code == 404
        assert "No numeric pH readings" in response.json()["detail"]
    finally:
        if sensor is not None:
            db.delete(sensor)
            db.flush()
        if asset is not None:
            db.delete(asset)
            db.flush()
        if zone is not None:
            db.delete(zone)
            db.flush()
        if city is not None:
            db.delete(city)
            db.flush()
        db.commit()
        db.close()


def test_infrastructure_overview(client):
    """Retrieve infrastructure breakdown and asset summary."""
    res = client.get("/api/v1/public/infrastructure?city_id=1")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] > 0
    assert "type_counts" in data
    assert isinstance(data["assets"], list)
    first_asset = data["assets"][0]
    assert "name" in first_asset
    assert "type" in first_asset
    assert "status" in first_asset


def test_public_notifications_announcements(client):
    """Retrieve public municipal announcements."""
    res = client.get("/api/v1/public/notifications")
    assert res.status_code == 200
    announcements = res.json()
    assert len(announcements) >= 1
    first = announcements[0]
    assert "title" in first
    assert "message" in first
    assert "notification_type" in first


def test_default_public_announcement_wording_is_simulated_and_factual():
    """Canonical defaults accurately describe the simulated platform scope."""
    messages = " ".join(
        announcement["message"]
        for announcement in DEFAULT_PUBLIC_ANNOUNCEMENTS
    ).lower()

    assert "four virtual cities and 16 zones" in messages
    assert "nominal ph" not in messages
    assert "all treatment facilities" not in messages
    assert "regulatory compliance" in messages


def test_submit_complaint_without_zone(client):
    """Submit complaint without zone selection (zone optional)."""
    payload = {"details": "Noticeable drop in tap water pressure during morning hours."}
    res = client.post("/api/v1/public/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["message"] == "Complaint submitted"
    assert "tracking_id" in data
    assert data["tracking_id"].startswith("CMP-")


def test_submit_complaint_with_zone(client):
    """Submit complaint with explicit valid zone ID."""
    payload = {
        "details": "Water appears slightly aerated with microbubbles in kitchen tap.",
        "zone_id": 1,
    }
    res = client.post("/api/v1/public/complaints", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert "tracking_id" in data
    assert data["tracking_id"].startswith("CMP-")


def test_submit_complaint_validation_too_short(client):
    """Reject complaint submission when details are under 5 characters."""
    res = client.post("/api/v1/public/complaints", json={"details": "Low"})
    assert res.status_code == 422


def test_submit_complaint_validation_empty(client):
    """Reject complaint submission when details are whitespace only."""
    res = client.post("/api/v1/public/complaints", json={"details": "    "})
    assert res.status_code == 422


def test_submit_complaint_validation_invalid_zone(client):
    """Reject complaint submission when specified zone does not exist."""
    res = client.post(
        "/api/v1/public/complaints",
        json={"details": "Valid complaint details but bogus zone", "zone_id": 99999},
    )
    assert res.status_code == 422


def test_track_complaint_valid_and_invalid(client):
    """Test tracking valid complaint by ID and 404 for invalid tracking ID."""
    # Submit first
    submit_res = client.post(
        "/api/v1/public/complaints",
        json={"details": "Pipeline vibration sound heard near main valve.", "zone_id": 2},
    )
    assert submit_res.status_code == 201
    tracking_id = submit_res.json()["tracking_id"]

    # Track valid
    track_res = client.get(f"/api/v1/public/complaints/{tracking_id}")
    assert track_res.status_code == 200
    track_data = track_res.json()
    assert track_data["tracking_id"] == tracking_id
    assert track_data["details"] == "Pipeline vibration sound heard near main valve."
    assert track_data["status"] == "Submitted"
    assert track_data["zone_id"] == 2
    assert track_data["zone_name"] is not None
    assert "city_name" in track_data
    assert "notifications" in track_data

    # Track invalid
    invalid_res = client.get("/api/v1/public/complaints/CMP-INVALID-99999")
    assert invalid_res.status_code == 404
    assert invalid_res.json()["detail"] == "Complaint not found"


def test_tracking_ids_are_unique_and_unpredictable(client):
    """Ensure consecutive complaints generate distinct high-entropy tracking IDs."""
    ids = set()
    for i in range(3):
        res = client.post(
            "/api/v1/public/complaints",
            json={"details": f"Automated unique tracking ID evaluation test #{i}"},
        )
        assert res.status_code == 201
        tid = res.json()["tracking_id"]
        assert tid not in ids
        assert len(tid) >= 12  # e.g. CMP-XXXXXXXX-XXXX
        ids.add(tid)
