from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database.database import Base
from backend.app.models import (
    Anomaly,
    Asset,
    AssetHealthScore,
    City,
    MaintenanceRecord,
    RiskScore,
    Sensor,
    SensorReading,
    User,
    Zone,
)
from backend.app.services import analytics_service
from backend.app.services.analytics_service import run_analytics_for_all


TEST_TABLES = [
    User.__table__,
    City.__table__,
    Zone.__table__,
    Asset.__table__,
    Sensor.__table__,
    SensorReading.__table__,
    Anomaly.__table__,
    AssetHealthScore.__table__,
    RiskScore.__table__,
    MaintenanceRecord.__table__,
]


@pytest.fixture
def db_session():
    """Create an isolated in-memory SQLite database for each test."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine, tables=TEST_TABLES)

    TestingSession = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    db = TestingSession()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine, tables=TEST_TABLES)
        engine.dispose()


def create_city_and_zone(db, name_prefix):
    city = City(city_name=f"{name_prefix} City")
    db.add(city)
    db.flush()

    zone = Zone(
        zone_name=f"{name_prefix} Zone",
        city_id=city.city_id,
    )
    db.add(zone)
    db.flush()
    return city, zone


def create_asset(
    db,
    zone,
    name,
    asset_type="Pipeline",
    now=None,
):
    asset = Asset(
        zone_id=zone.zone_id,
        asset_name=name,
        asset_type=asset_type,
        status="Operational",
        updated_at=now or datetime.now(),
    )
    db.add(asset)
    db.flush()
    return asset


def create_sensor(db, asset, sensor_type, sensor_name):
    sensor = Sensor(
        asset_id=asset.asset_id,
        sensor_type=sensor_type,
        sensor_name=sensor_name,
        status="Active",
    )
    db.add(sensor)
    db.flush()
    return sensor


def create_numeric_reading(db, sensor, value, timestamp):
    reading = SensorReading(
        sensor_id=sensor.sensor_id,
        reading_value_numeric=value,
        reading_value_text=None,
        timestamp=timestamp,
        status="Normal",
    )
    db.add(reading)
    db.flush()
    return reading


def create_text_reading(db, sensor, value, timestamp):
    reading = SensorReading(
        sensor_id=sensor.sensor_id,
        reading_value_numeric=None,
        reading_value_text=value,
        timestamp=timestamp,
        status="Normal",
    )
    db.add(reading)
    db.flush()
    return reading


def create_active_anomaly(db, asset, detected_at):
    anomaly = Anomaly(
        asset_id=asset.asset_id,
        sensor_reading_id=None,
        anomaly_type="Existing Active Anomaly",
        description="Seeded active anomaly for score calculation.",
        detected_at=detected_at,
        status="Active",
    )
    db.add(anomaly)
    return anomaly


def decision_for(result, asset_id):
    return next(
        decision
        for decision in result["asset_decisions"]
        if decision["asset_id"] == asset_id
    )


def test_processing_persists_anomaly_and_scores(db_session):
    """Verify anomaly detection, score calculation and persistence."""

    now = datetime.now()

    city = City(city_name="Analytics Test City")
    db_session.add(city)
    db_session.flush()

    zone = Zone(
        zone_name="Analytics Test Zone",
        city_id=city.city_id,
    )
    db_session.add(zone)
    db_session.flush()

    asset = Asset(
        zone_id=zone.zone_id,
        asset_name="Analytics Test Pipeline",
        asset_type="Pipeline",
        status="Operational",
        updated_at=now,
    )
    db_session.add(asset)
    db_session.flush()

    sensor = Sensor(
        asset_id=asset.asset_id,
        sensor_type="Pressure",
        sensor_name="TEST-PRESSURE",
        status="Active",
    )
    db_session.add(sensor)
    db_session.flush()

    reading = SensorReading(
        sensor_id=sensor.sensor_id,
        reading_value_numeric=65.0,
        reading_value_text=None,
        timestamp=now,
        status="Normal",
    )
    db_session.add(reading)
    db_session.commit()

    result = run_analytics_for_all(db_session)

    assert result["assets_processed"] == 1
    assert result["total_anomalies"] == 1
    assert len(result["asset_decisions"]) == 1
    assert len(result["maintenance_queue"]) == 1

    anomaly = db_session.query(Anomaly).one()

    assert anomaly.asset_id == asset.asset_id
    assert anomaly.sensor_reading_id == reading.reading_id
    assert anomaly.anomaly_type == "High Pressure"
    assert anomaly.status == "Active"

    ahs = (
        db_session.query(AssetHealthScore)
        .filter(AssetHealthScore.asset_id == asset.asset_id)
        .one()
    )

    risk = (
        db_session.query(RiskScore)
        .filter(RiskScore.asset_id == asset.asset_id)
        .one()
    )

    assert float(ahs.score) == 90.0
    assert float(risk.score) == 10.0

    decision = result["asset_decisions"][0]

    assert decision["ahs"] == 90.0
    assert decision["rs"] == 10.0
    assert decision["anomaly_count"] == 1
    assert decision["maintenance_priority"] == 25.0
    assert "Recommended: Monitor" in decision["recommendation"]


def test_processing_deduplicates_recent_unresolved_anomaly(db_session):
    """Do not create a duplicate within the five-minute window."""

    now = datetime.now()

    city = City(city_name="Dedup Test City")
    db_session.add(city)
    db_session.flush()

    zone = Zone(
        zone_name="Dedup Test Zone",
        city_id=city.city_id,
    )
    db_session.add(zone)
    db_session.flush()

    asset = Asset(
        zone_id=zone.zone_id,
        asset_name="Dedup Test Pipeline",
        asset_type="Pipeline",
        status="Operational",
        updated_at=now,
    )
    db_session.add(asset)
    db_session.flush()

    sensor = Sensor(
        asset_id=asset.asset_id,
        sensor_type="Pressure",
        sensor_name="DEDUP-PRESSURE",
        status="Active",
    )
    db_session.add(sensor)
    db_session.flush()

    reading = SensorReading(
        sensor_id=sensor.sensor_id,
        reading_value_numeric=65.0,
        reading_value_text=None,
        timestamp=now,
        status="Normal",
    )
    db_session.add(reading)
    db_session.flush()

    existing_anomaly = Anomaly(
        asset_id=asset.asset_id,
        sensor_reading_id=reading.reading_id,
        anomaly_type="High Pressure",
        description="Previously detected high pressure.",
        detected_at=now - timedelta(minutes=2),
        status="Active",
    )
    db_session.add(existing_anomaly)
    db_session.commit()

    result = run_analytics_for_all(db_session)

    anomalies = (
        db_session.query(Anomaly)
        .filter(Anomaly.asset_id == asset.asset_id)
        .all()
    )

    assert result["total_anomalies"] == 0
    assert len(anomalies) == 1
    assert anomalies[0].anomaly_type == "High Pressure"

    decision = result["asset_decisions"][0]

    assert decision["anomaly_count"] == 1
    assert decision["ahs"] == 90.0
    assert decision["rs"] == 10.0


def test_processing_uses_newer_normal_reading_for_sensor(db_session):
    """An older abnormal reading must not override a newer normal one."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Latest Reading")
    asset = create_asset(db_session, zone, "Latest Reading Pipeline", now=now)
    sensor = create_sensor(db_session, asset, "Pressure", "LATEST-PRESSURE")
    create_numeric_reading(db_session, sensor, 65.0, now - timedelta(minutes=10))
    newer_reading = create_numeric_reading(
        db_session,
        sensor,
        50.0,
        now - timedelta(minutes=1),
    )
    db_session.commit()

    result = run_analytics_for_all(db_session)

    assert result["total_anomalies"] == 0
    assert db_session.query(Anomaly).count() == 0
    assert decision_for(result, asset.asset_id)["ahs"] == 100.0
    assert newer_reading.reading_id is not None


def test_processing_uses_higher_reading_id_for_equal_timestamps(db_session):
    """Equal timestamps are resolved by descending reading ID."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Reading Tie Break")
    asset = create_asset(db_session, zone, "Tie Break Pipeline", now=now)
    sensor = create_sensor(db_session, asset, "Pressure", "TIE-BREAK-PRESSURE")
    create_numeric_reading(db_session, sensor, 50.0, now - timedelta(minutes=1))
    selected_reading = create_numeric_reading(
        db_session,
        sensor,
        65.0,
        now - timedelta(minutes=1),
    )
    db_session.commit()

    result = run_analytics_for_all(db_session)
    anomaly = db_session.query(Anomaly).one()

    assert result["total_anomalies"] == 1
    assert anomaly.asset_id == asset.asset_id
    assert anomaly.sensor_reading_id == selected_reading.reading_id
    assert anomaly.anomaly_type == "High Pressure"


def test_processing_uses_newest_qualifying_sensor_for_same_anomaly_type(
    db_session,
):
    """One stored anomaly uses the newest qualifying same-parameter reading."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Multiple Pressure")
    asset = create_asset(db_session, zone, "Multiple Pressure Pipeline", now=now)
    newer_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "NEWER-HIGH-PRESSURE",
    )
    older_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "OLDER-HIGH-PRESSURE",
    )
    newer_reading = create_numeric_reading(
        db_session,
        newer_sensor,
        70.0,
        now - timedelta(minutes=1),
    )
    create_numeric_reading(
        db_session,
        older_sensor,
        65.0,
        now - timedelta(minutes=10),
    )
    db_session.commit()

    result = run_analytics_for_all(db_session)
    anomaly = db_session.query(Anomaly).one()

    assert result["total_anomalies"] == 1
    assert anomaly.anomaly_type == "High Pressure"
    assert anomaly.asset_id == asset.asset_id
    assert anomaly.sensor_reading_id == newer_reading.reading_id


def test_processing_uses_higher_reading_id_across_same_parameter_sensors(
    db_session,
):
    """Same-parameter sensor ties select the higher reading ID."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Multiple Pressure Tie")
    asset = create_asset(db_session, zone, "Multiple Pressure Tie Pipeline", now=now)
    first_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "FIRST-HIGH-PRESSURE",
    )
    second_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "SECOND-HIGH-PRESSURE",
    )
    timestamp = now - timedelta(minutes=1)
    create_numeric_reading(db_session, second_sensor, 65.0, timestamp)
    selected_reading = create_numeric_reading(
        db_session,
        first_sensor,
        70.0,
        timestamp,
    )
    db_session.commit()

    run_analytics_for_all(db_session)
    anomaly = db_session.query(Anomaly).one()

    assert anomaly.anomaly_type == "High Pressure"
    assert anomaly.sensor_reading_id == selected_reading.reading_id


def test_processing_selects_latest_parameter_readings_for_possible_leak(
    db_session,
):
    """Possible Leak uses the latest flow and pressure across sensors."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Multiple Leak Sensors")
    asset = create_asset(db_session, zone, "Multiple Leak Pipeline", now=now)
    newest_pressure_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "NEWEST-LOW-PRESSURE",
    )
    newest_flow_sensor = create_sensor(
        db_session,
        asset,
        "Flow",
        "NEWEST-LOW-FLOW",
    )
    older_pressure_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "OLDER-NORMAL-PRESSURE",
    )
    older_flow_sensor = create_sensor(
        db_session,
        asset,
        "Flow",
        "OLDER-NORMAL-FLOW",
    )
    newest_pressure = create_numeric_reading(
        db_session,
        newest_pressure_sensor,
        35.0,
        now - timedelta(minutes=1),
    )
    newest_flow = create_numeric_reading(
        db_session,
        newest_flow_sensor,
        70.0,
        now - timedelta(minutes=1),
    )
    create_numeric_reading(
        db_session,
        older_pressure_sensor,
        50.0,
        now - timedelta(minutes=10),
    )
    create_numeric_reading(
        db_session,
        older_flow_sensor,
        90.0,
        now - timedelta(minutes=10),
    )
    db_session.commit()

    result = run_analytics_for_all(db_session)
    leak = (
        db_session.query(Anomaly)
        .filter(Anomaly.anomaly_type == "Possible Leak")
        .one()
    )

    assert result["total_anomalies"] == 3
    assert leak.asset_id == asset.asset_id
    assert leak.sensor_reading_id == newest_flow.reading_id
    assert f"Pressure reading ID: {newest_pressure.reading_id}" in leak.description


def test_processing_selects_latest_parameter_readings_for_equipment_failure(
    db_session,
):
    """Equipment failure uses the latest pressure and equipment status."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Multiple Equipment Sensors")
    asset = create_asset(
        db_session,
        zone,
        "Multiple Equipment Pump Station",
        asset_type="PumpStation",
        now=now,
    )
    newest_pressure_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "NEWEST-LOW-PRESSURE",
    )
    newest_status_sensor = create_sensor(
        db_session,
        asset,
        "Equipment Condition",
        "NEWEST-EQUIPMENT-STATUS",
    )
    older_pressure_sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        "OLDER-NORMAL-PRESSURE",
    )
    older_status_sensor = create_sensor(
        db_session,
        asset,
        "Equipment Condition",
        "OLDER-EQUIPMENT-STATUS",
    )
    newest_pressure = create_numeric_reading(
        db_session,
        newest_pressure_sensor,
        55.0,
        now - timedelta(minutes=1),
    )
    newest_status = create_text_reading(
        db_session,
        newest_status_sensor,
        "OFF",
        now - timedelta(minutes=1),
    )
    create_numeric_reading(
        db_session,
        older_pressure_sensor,
        70.0,
        now - timedelta(minutes=10),
    )
    create_text_reading(
        db_session,
        older_status_sensor,
        "ON",
        now - timedelta(minutes=10),
    )
    db_session.commit()

    result = run_analytics_for_all(db_session)
    failure = (
        db_session.query(Anomaly)
        .filter(Anomaly.anomaly_type == "Possible Equipment Failure")
        .one()
    )

    assert result["total_anomalies"] == 2
    assert failure.asset_id == asset.asset_id
    assert failure.sensor_reading_id == newest_status.reading_id
    assert (
        f"{float(newest_pressure.reading_value_numeric):.2f} PSI"
        in failure.description
    )


@pytest.mark.parametrize("resolved_status", ["resolved", "closed", "completed"])
def test_processing_recreates_recent_resolved_anomalies(
    db_session,
    resolved_status,
):
    """Resolved-status anomalies do not suppress or count as active."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, f"{resolved_status.title()} Status")
    asset = create_asset(
        db_session,
        zone,
        f"{resolved_status.title()} Pipeline",
        now=now,
    )
    sensor = create_sensor(
        db_session,
        asset,
        "Pressure",
        f"{resolved_status.upper()}-PRESSURE",
    )
    reading = create_numeric_reading(db_session, sensor, 65.0, now)
    db_session.add(Anomaly(
        asset_id=asset.asset_id,
        sensor_reading_id=reading.reading_id,
        anomaly_type="High Pressure",
        description="Previously resolved high pressure.",
        detected_at=now - timedelta(minutes=2),
        status=resolved_status,
    ))
    db_session.commit()

    result = run_analytics_for_all(db_session)
    anomalies = (
        db_session.query(Anomaly)
        .filter(Anomaly.asset_id == asset.asset_id)
        .order_by(Anomaly.anomaly_id.asc())
        .all()
    )
    decision = decision_for(result, asset.asset_id)

    assert result["total_anomalies"] == 1
    assert len(anomalies) == 2
    assert anomalies[0].status == resolved_status
    assert anomalies[1].status == "Active"
    assert anomalies[1].sensor_reading_id == reading.reading_id
    assert decision["anomaly_count"] == 1
    assert decision["ahs"] == 90.0


def test_processing_counts_only_maintenance_within_lookback(db_session):
    """Only maintenance records in the preceding seven days reduce AHS."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Maintenance Lookback")
    asset = create_asset(db_session, zone, "Maintenance Pipeline", now=now)
    officer = User(
        name="Maintenance Test Officer",
        email="maintenance-lookback@example.test",
        password_hash="not-used-by-service",
        role="Maintenance Officer",
    )
    db_session.add(officer)
    db_session.flush()

    for maintenance_date in (now - timedelta(days=1), now - timedelta(days=6)):
        db_session.add(MaintenanceRecord(
            asset_id=asset.asset_id,
            maintenance_officer_id=officer.user_id,
            maintenance_date=maintenance_date,
            maintenance_details="Recent maintenance.",
            status="Completed",
        ))

    db_session.add(MaintenanceRecord(
        asset_id=asset.asset_id,
        maintenance_officer_id=officer.user_id,
        maintenance_date=now - timedelta(days=8),
        maintenance_details="Older maintenance.",
        status="Completed",
    ))
    db_session.commit()

    result = run_analytics_for_all(db_session)
    ahs = db_session.query(AssetHealthScore).one()
    decision = decision_for(result, asset.asset_id)

    assert float(ahs.score) == 96.0
    assert decision["anomaly_count"] == 0
    assert decision["ahs"] == 96.0
    assert decision["rs"] == 4.0


def test_processing_calculates_risk_scores_for_all_criticalities(db_session):
    """Risk scores use the approved criticality mapping for every type."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Criticality")
    expected_scores = {
        "TreatmentFacility": 15.0,
        "PumpStation": 13.0,
        "Reservoir": 12.0,
        "Pipeline": 10.0,
        "Valve": 8.0,
    }
    assets = {}

    for asset_type in expected_scores:
        asset = create_asset(
            db_session,
            zone,
            f"{asset_type} Criticality Asset",
            asset_type=asset_type,
            now=now,
        )
        create_active_anomaly(db_session, asset, now - timedelta(hours=1))
        assets[asset_type] = asset

    db_session.commit()
    result = run_analytics_for_all(db_session)

    for asset_type, expected_rs in expected_scores.items():
        asset = assets[asset_type]
        persisted_risk = (
            db_session.query(RiskScore)
            .filter(RiskScore.asset_id == asset.asset_id)
            .one()
        )
        decision = decision_for(result, asset.asset_id)

        assert float(persisted_risk.score) == expected_rs
        assert decision["ahs"] == 90.0
        assert decision["rs"] == expected_rs
        assert decision["anomaly_count"] == 1


def test_processing_ranks_maintenance_priorities_with_asset_id_tiebreaker(
    db_session,
):
    """Priorities sort descending, with asset IDs ascending for ties."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Priority Ranking")
    treatment = create_asset(
        db_session,
        zone,
        "Treatment Priority Asset",
        asset_type="TreatmentFacility",
        now=now,
    )
    pump = create_asset(
        db_session,
        zone,
        "Pump Priority Asset",
        asset_type="PumpStation",
        now=now,
    )
    pipeline_one = create_asset(
        db_session,
        zone,
        "Pipeline Priority Asset One",
        asset_type="Pipeline",
        now=now,
    )
    pipeline_two = create_asset(
        db_session,
        zone,
        "Pipeline Priority Asset Two",
        asset_type="Pipeline",
        now=now,
    )

    for asset in (treatment, pump, pipeline_one, pipeline_two):
        create_active_anomaly(db_session, asset, now - timedelta(hours=1))

    db_session.commit()
    result = run_analytics_for_all(db_session)
    decisions = result["asset_decisions"]
    priorities = {
        decision["asset_id"]: decision["maintenance_priority"]
        for decision in decisions
    }

    assert priorities[treatment.asset_id] == 35.0
    assert priorities[pump.asset_id] == 31.0
    assert priorities[pipeline_one.asset_id] == 25.0
    assert priorities[pipeline_two.asset_id] == 25.0
    assert [decision["asset_id"] for decision in decisions] == [
        treatment.asset_id,
        pump.asset_id,
        pipeline_one.asset_id,
        pipeline_two.asset_id,
    ]


def test_processing_limits_maintenance_queue_to_top_ten(db_session):
    """The maintenance queue contains the first ten ranked decisions."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Maintenance Queue")
    assets = [
        create_asset(
            db_session,
            zone,
            f"Queue Pipeline {index}",
            now=now,
        )
        for index in range(11)
    ]
    db_session.commit()

    result = run_analytics_for_all(db_session)

    assert len(result["asset_decisions"]) == 11
    assert {decision["asset_id"] for decision in result["asset_decisions"]} == {
        asset.asset_id for asset in assets
    }
    assert len(result["maintenance_queue"]) == 10
    assert result["maintenance_queue"] == result["asset_decisions"][:10]
    assert [decision["asset_id"] for decision in result["maintenance_queue"]] == [
        asset.asset_id for asset in assets[:10]
    ]


def test_processing_handles_empty_database(db_session):
    """Processing an empty database returns empty analytics outputs."""

    result = run_analytics_for_all(db_session)

    assert result["assets_processed"] == 0
    assert result["total_anomalies"] == 0
    assert result["asset_decisions"] == []
    assert result["maintenance_queue"] == []
    assert db_session.query(Anomaly).count() == 0
    assert db_session.query(AssetHealthScore).count() == 0
    assert db_session.query(RiskScore).count() == 0


def test_processing_rolls_back_all_generated_records_after_failure(
    db_session,
    monkeypatch,
):
    """A processing failure rolls back generated anomalies and scores."""

    now = datetime.now()
    _, zone = create_city_and_zone(db_session, "Rollback")
    first_asset = create_asset(db_session, zone, "Rollback First Pipeline", now=now)
    second_asset = create_asset(db_session, zone, "Rollback Second Pipeline", now=now)
    sensor = create_sensor(
        db_session,
        first_asset,
        "Pressure",
        "ROLLBACK-FIRST-PRESSURE",
    )
    create_numeric_reading(db_session, sensor, 65.0, now)
    db_session.commit()

    original_count_active = analytics_service._count_active_anomalies
    calls = {"count": 0}

    def fail_while_processing_second_asset(db, asset_id):
        calls["count"] += 1
        if calls["count"] == 2:
            raise RuntimeError("Controlled analytics processing failure")
        return original_count_active(db, asset_id)

    monkeypatch.setattr(
        analytics_service,
        "_count_active_anomalies",
        fail_while_processing_second_asset,
    )

    with pytest.raises(RuntimeError, match="Controlled analytics processing failure"):
        run_analytics_for_all(db_session)

    assert calls["count"] == 2
    assert db_session.query(Asset).count() == 2
    assert db_session.query(Sensor).count() == 1
    assert db_session.query(SensorReading).count() == 1
    assert db_session.query(Anomaly).count() == 0
    assert db_session.query(AssetHealthScore).count() == 0
    assert db_session.query(RiskScore).count() == 0
