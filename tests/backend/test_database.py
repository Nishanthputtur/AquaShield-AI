"""
Integration tests for backend/app/database/seed.py and
backend/app/services/monitoring_service.py.

Run from the project root:
    python -m pytest tests/backend/test_database.py -v

Uses the real PostgreSQL database `aquashield`. Requires PostgreSQL to
be running and the 18 tables to exist (Base.metadata.create_all()).

The fixture at module scope seeds the database once before the first
test runs. Tests that touch sensor_readings delete them at start, so
test order does not matter for correctness.

No simulator code is modified by these tests.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError

from backend.app.database.connection import SessionLocal
from backend.app.database.database import Base
from backend.app.database.seed import (
    seed_inventory,
    _verify_name_uniqueness,
    ZONE_NAME_OVERRIDES,
)
from backend.app.models import (
    Asset,
    City,
    Pipeline,
    PumpStation,
    Reservoir,
    Sensor,
    SensorReading,
    TreatmentFacility,
    Valve,
    Zone,
)
from backend.app.services.monitoring_service import (
    PARAMETER_BY_CLASS,
    NUMERIC_EQUIPMENT_PARAMETERS,
    get_recent_readings,
    persist_readings,
)
from simulator.city.virtual_city import create_virtual_city
from simulator.sensors import generate_all_readings, initialize_sensors


# ----------------------------------------------------------------------
# Fixture: ensure the DB is seeded once for the module
# ----------------------------------------------------------------------

@pytest.fixture(scope="module", autouse=True)
def seeded_database():
    """Ensure the database contains the full seeded inventory.

    seed_inventory() is idempotent, so this works whether the DB was
    previously seeded or is empty.
    """
    seed_inventory()
    yield

@pytest.fixture(autouse=True)
def clean_readings():
    """Empty sensor_readings before and after every test.

    Ensures tests that count readings start from zero and that the
    database is left clean after the module finishes.
    """
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()
    finally:
        db.close()

def _counts(db):
    """Return the inventory counts for the nine seeded tables."""
    return {
        "cities": db.query(City).count(),
        "zones": db.query(Zone).count(),
        "assets": db.query(Asset).count(),
        "treatment_facilities": db.query(TreatmentFacility).count(),
        "reservoirs": db.query(Reservoir).count(),
        "pump_stations": db.query(PumpStation).count(),
        "pipelines": db.query(Pipeline).count(),
        "valves": db.query(Valve).count(),
        "sensors": db.query(Sensor).count(),
    }


# ----------------------------------------------------------------------
# Test 1: 18 tables registered in ORM metadata
# ----------------------------------------------------------------------

def test_eighteen_tables_registered():
    """The ORM must declare exactly the 18 approved tables."""
    assert len(Base.metadata.tables) == 18
    expected = {
        "anomalies",
        "asset_health_scores",
        "assets",
        "cities",
        "complaints",
        "inspections",
        "maintenance_records",
        "notifications",
        "pipelines",
        "pump_stations",
        "reservoirs",
        "risk_scores",
        "sensor_readings",
        "sensors",
        "treatment_facilities",
        "users",
        "valves",
        "zones",
    }
    assert set(Base.metadata.tables.keys()) == expected


# ----------------------------------------------------------------------
# Test 2: seed produces exact expected inventory
# ----------------------------------------------------------------------

def test_seeded_inventory_counts():
    db = SessionLocal()
    try:
        counts = _counts(db)
    finally:
        db.close()

    assert counts == {
        "cities": 4,
        "zones": 16,
        "assets": 108,
        "treatment_facilities": 8,
        "reservoirs": 8,
        "pump_stations": 12,
        "pipelines": 48,
        "valves": 32,
        "sensors": 328,
    }


# ----------------------------------------------------------------------
# Test 3: every asset has exactly one matching subtype row
# ----------------------------------------------------------------------

def test_every_asset_has_matching_subtype():
    """Each asset's asset_type must correspond to exactly one row in
    the matching subtype table."""
    db = SessionLocal()
    try:
        assets = db.query(Asset).all()
        assert len(assets) == 108

        for asset in assets:
            if asset.asset_type == "TreatmentFacility":
                n = db.query(TreatmentFacility).filter_by(
                    asset_id=asset.asset_id
                ).count()
            elif asset.asset_type == "Reservoir":
                n = db.query(Reservoir).filter_by(
                    asset_id=asset.asset_id
                ).count()
            elif asset.asset_type == "PumpStation":
                n = db.query(PumpStation).filter_by(
                    asset_id=asset.asset_id
                ).count()
            elif asset.asset_type == "Pipeline":
                n = db.query(Pipeline).filter_by(
                    asset_id=asset.asset_id
                ).count()
            elif asset.asset_type == "Valve":
                n = db.query(Valve).filter_by(
                    asset_id=asset.asset_id
                ).count()
            else:
                pytest.fail(f"Unknown asset_type: {asset.asset_type!r}")

            assert n == 1, (
                f"{asset.asset_name} ({asset.asset_type}) has "
                f"{n} subtype rows, expected 1"
            )
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 4: repeated seeding is idempotent
# ----------------------------------------------------------------------

def test_idempotent_seeding():
    """Calling seed_inventory() again must not change row counts."""
    db = SessionLocal()
    try:
        before = _counts(db)
    finally:
        db.close()

    seed_inventory()

    db = SessionLocal()
    try:
        after = _counts(db)
    finally:
        db.close()

    assert before == after, (
        f"Seeding was not idempotent. Before: {before}, after: {after}"
    )


# ----------------------------------------------------------------------
# Test 5: Zorawarpur zone names use approved design overrides
# ----------------------------------------------------------------------

def test_zorawarpur_zone_names_overridden():
    """The four Zorawarpur zones must use the approved design names."""
    expected = set(ZONE_NAME_OVERRIDES.values())
    assert expected == {
        "Z-01 North Heights",
        "Z-02 Central Zora",
        "Z-03 Zora Industrial Belt",
        "Z-04 New Zora",
    }

    db = SessionLocal()
    try:
        zorawarpur = db.query(City).filter_by(city_name="Zorawarpur").one()
        zone_names = {
            z.zone_name
            for z in db.query(Zone).filter_by(city_id=zorawarpur.city_id).all()
        }
    finally:
        db.close()

    assert zone_names == expected


# ----------------------------------------------------------------------
# Test 6: asset ID mapping has 108 entries
# ----------------------------------------------------------------------

def test_asset_id_mapping_complete():
    """seed_inventory returns a complete simulator-asset -> DB-asset map."""
    maps = seed_inventory()
    assert len(maps.asset_id_by_simulator_id) == 108
    for sim_id, db_id in maps.asset_id_by_simulator_id.items():
        assert isinstance(sim_id, str)
        assert isinstance(db_id, int)
    assert "C1-P-001" in maps.asset_id_by_simulator_id


# ----------------------------------------------------------------------
# Test 7: sensor ID mapping has 328 entries
# ----------------------------------------------------------------------

def test_sensor_id_mapping_complete():
    """seed_inventory returns a complete simulator-sensor -> DB-sensor map."""
    maps = seed_inventory()
    assert len(maps.sensor_id_by_simulator_id) == 328
    for sim_id, db_id in maps.sensor_id_by_simulator_id.items():
        assert isinstance(sim_id, str)
        assert isinstance(db_id, int)


# ----------------------------------------------------------------------
# Test 8: _verify_name_uniqueness catches duplicate asset_name
# ----------------------------------------------------------------------

def test_duplicate_asset_name_detected():
    """_verify_name_uniqueness must reject a duplicated asset_name."""
    db = SessionLocal()
    try:
        zone_row = db.query(Zone).first()
        dup = Asset(
            zone_id=zone_row.zone_id,
            asset_name="C1-P-001",
            asset_type="Pipeline",
            status="operational",
            parent_asset_id=None,
            updated_at=datetime.now(),
        )
        db.add(dup)
        db.flush()

        with pytest.raises(RuntimeError, match="Duplicate asset_name"):
            _verify_name_uniqueness(db)
    finally:
        db.rollback()
        db.close()


# ----------------------------------------------------------------------
# Test 9: numeric readings land in reading_value_numeric
# ----------------------------------------------------------------------

def test_numeric_reading_stored_in_numeric_column():
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()

        create_virtual_city()
        initialize_sensors()
        readings = generate_all_readings()

        pressure = [r for r in readings if r["parameter"] == "Pressure"][:5]
        assert len(pressure) == 5

        n = persist_readings(db, pressure)
        db.commit()
        assert n == 5

        stored = db.query(SensorReading).all()
        assert len(stored) == 5
        for s in stored:
            assert s.reading_value_numeric is not None
            assert s.reading_value_text is None
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 10: equipment readings land in reading_value_text
# ----------------------------------------------------------------------

def test_equipment_reading_stored_in_text_column():
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()

        create_virtual_city()
        initialize_sensors()
        readings = generate_all_readings()

        equip = [
            r for r in readings
            if r["parameter"] in NUMERIC_EQUIPMENT_PARAMETERS
            or r["parameter"] == "Equipment Status"
        ][:5]
        assert len(equip) == 5

        n = persist_readings(db, equip)
        db.commit()
        assert n == 5

        stored = db.query(SensorReading).all()
        for s in stored:
            assert s.reading_value_numeric is None
            assert s.reading_value_text is not None
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 11: numeric equipment value round-trips as float
# ----------------------------------------------------------------------

def test_numeric_equipment_reconstruction():
    """Temperature is stored as text but reconstructed as float."""
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()

        create_virtual_city()
        initialize_sensors()
        readings = generate_all_readings()

        temp = [r for r in readings if r["parameter"] == "Temperature"][:1]
        assert len(temp) == 1
        original = temp[0]

        persist_readings(db, [original])
        db.commit()

        recent = get_recent_readings(db, limit=1)
        assert len(recent) == 1
        reconstructed = recent[0]

        assert reconstructed["parameter"] == "Temperature"
        assert isinstance(reconstructed["value"], float), (
            f"Expected float, got {type(reconstructed['value']).__name__}"
        )
        assert abs(reconstructed["value"] - float(original["value"])) < 0.01
        assert reconstructed["unit"] == "°C"
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 12: Equipment Status round-trips as string
# ----------------------------------------------------------------------

def test_text_equipment_reconstruction():
    """Equipment Status is reconstructed as a string, not a float."""
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()

        create_virtual_city()
        initialize_sensors()
        readings = generate_all_readings()

        status = [
            r for r in readings if r["parameter"] == "Equipment Status"
        ][:1]
        assert len(status) == 1
        original = status[0]

        persist_readings(db, [original])
        db.commit()

        recent = get_recent_readings(db, limit=1)
        reconstructed = recent[0]

        assert reconstructed["parameter"] == "Equipment Status"
        assert isinstance(reconstructed["value"], str), (
            f"Expected str, got {type(reconstructed['value']).__name__}"
        )
        assert reconstructed["value"] in {"ON", "OFF", "STANDBY"}
        assert reconstructed["unit"] == "STATUS"
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 13: CHECK constraint rejects row with both value columns NULL
# ----------------------------------------------------------------------

def test_check_constraint_rejects_both_null():
    db = SessionLocal()
    try:
        sensor_row = db.query(Sensor).first()
        bad = SensorReading(
            sensor_id=sensor_row.sensor_id,
            reading_value_numeric=None,
            reading_value_text=None,
            timestamp=datetime.now(),
            status=None,
        )
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        db.rollback()
        db.close()


# ----------------------------------------------------------------------
# Test 14: CHECK constraint rejects row with both value columns set
# ----------------------------------------------------------------------

def test_check_constraint_rejects_both_set():
    db = SessionLocal()
    try:
        sensor_row = db.query(Sensor).first()
        bad = SensorReading(
            sensor_id=sensor_row.sensor_id,
            reading_value_numeric=42.0,
            reading_value_text="42.0",
            timestamp=datetime.now(),
            status=None,
        )
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.flush()
    finally:
        db.rollback()
        db.close()


# ----------------------------------------------------------------------
# Test 15: full 328-reading round-trip preserves schema and parameter set
# ----------------------------------------------------------------------

def test_full_round_trip_328():
    """Full 328-reading round-trip. Verifies both:
        (a) the storage column split (248 numeric / 80 text in DB)
        (b) the reconstruction type split (316 float / 12 str after parse)
    """
    db = SessionLocal()
    try:
        db.query(SensorReading).delete()
        db.commit()

        create_virtual_city()
        initialize_sensors()
        readings = generate_all_readings()
        assert len(readings) == 328

        persist_readings(db, readings)
        db.commit()

        # --- (a) Storage split: verify the DB columns directly ---
        from sqlalchemy import text as sql_text

        numeric_col_count = db.execute(
            sql_text(
                "SELECT COUNT(*) FROM sensor_readings "
                "WHERE reading_value_numeric IS NOT NULL"
            )
        ).scalar()
        text_col_count = db.execute(
            sql_text(
                "SELECT COUNT(*) FROM sensor_readings "
                "WHERE reading_value_text IS NOT NULL"
            )
        ).scalar()

        # 248 non-equipment numeric readings -> numeric column
        # 80 equipment readings -> text column
        assert numeric_col_count == 248, (
            f"numeric column has {numeric_col_count} rows, expected 248"
        )
        assert text_col_count == 80, (
            f"text column has {text_col_count} rows, expected 80"
        )

        # --- (b) Reconstruction split: verify the returned values ---
        recent = get_recent_readings(db, limit=328)
        assert len(recent) == 328

        for r in recent:
            assert set(r.keys()) == {
                "sensor_id", "asset_id", "parameter", "value", "unit", "timestamp"
            }
            assert r["parameter"] in PARAMETER_BY_CLASS.values()

        numeric_count = sum(1 for r in recent if isinstance(r["value"], float))
        text_count = sum(1 for r in recent if isinstance(r["value"], str))
        assert numeric_count + text_count == 328

        # After reconstruction:
        #   248 non-equipment numeric -> float
        #    68 numeric equipment params -> parsed back to float
        #    12 Equipment Status -> str
        assert numeric_count == 316, (
            f"reconstruction has {numeric_count} floats, expected 316"
        )
        assert text_count == 12, (
            f"reconstruction has {text_count} strings, expected 12"
        )
    finally:
        db.close()


# ----------------------------------------------------------------------
# Test 16: seed_inventory propagates errors and rolls back
# ----------------------------------------------------------------------

def test_seed_rollback_on_verify_failure(monkeypatch):
    """If verification fails, seed_inventory propagates the error and
    leaves the database in its previous state (no partial changes)."""
    from backend.app.database import seed as seed_module

    def failing_verify(db):
        raise RuntimeError("injected failure for test")

    monkeypatch.setattr(seed_module, "_verify_counts", failing_verify)

    db = SessionLocal()
    try:
        before = _counts(db)
    finally:
        db.close()

    with pytest.raises(RuntimeError, match="injected failure"):
        seed_inventory()

    db = SessionLocal()
    try:
        after = _counts(db)
    finally:
        db.close()

    assert before == after, (
        f"Rollback did not restore state. Before: {before}, after: {after}"
    )