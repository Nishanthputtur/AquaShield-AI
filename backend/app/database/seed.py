"""
Inventory seeding for AquaShield AI.

Populates PostgreSQL with the virtual city inventory from the simulator.
Idempotent: repeated runs do not create duplicates.

Identity mapping
----------------
The simulator uses string identifiers (`C1-P-001`), the database uses
integer primary keys. This module stores:

    - simulator asset ID   in `assets.asset_name`
    - simulator sensor ID  in `sensors.sensor_name`

and returns in-memory maps for Step 5:

    - simulator_asset_id  -> DB asset_id  (int)
    - simulator_sensor_id -> DB sensor_id (int)

Neither column is documented as UNIQUE in the schema. Uniqueness is
enforced here in application logic by rejecting ambiguous matches
during lookup, and verified proactively by `_verify_name_uniqueness`
before commit.

Five binding decisions (M2 Step 4, documented in
docs/database/model_audit.txt):

    1. assets.status          = "operational"
    2. sensors.status         = "active"
    3. assets.parent_asset_id = NULL for all 108 assets
    4. Equipment Condition readings -> reading_value_text (Step 5)
    5. Name uniqueness verified before commit

Zone names
----------
The simulator generates generic zone names ("Zorawarpur Zone A").
The approved project design specifies the four Zorawarpur zone names.
Overrides are applied at seed time only; M1 is untouched. Only
Zorawarpur has approved names in the project record; the other three
cities use the simulator-generated names.

Descriptions
------------
cities.description and zones.description remain NULL. The project
specification does not define them.

No schema changes. No extra columns. No extra constraints.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.database.connection import SessionLocal
from backend.app.models import (
    Asset,
    City,
    Pipeline,
    PumpStation,
    Reservoir,
    Sensor,
    TreatmentFacility,
    Valve,
    Zone,
)
from simulator.city.assets import AssetType
from simulator.city.virtual_city import create_virtual_city
from simulator.sensors import initialize_sensors
from simulator.sensors.pressure import PressureSensor
from simulator.sensors.flow import FlowSensor
from simulator.sensors.equipment import (
    TemperatureSensor,
    VibrationSensor,
    PowerSensor,
    EquipmentStatusSensor,
    PositionSensor,
)
from simulator.sensors.water_quality import (
    LevelSensor,
    WaterTemperatureSensor,
    pHSensor,
    TurbiditySensor,
)


# ----------------------------------------------------------------------
# Decisions 1 and 2 — approved status values
# ----------------------------------------------------------------------

ASSET_STATUS = "operational"
SENSOR_STATUS = "active"


# ----------------------------------------------------------------------
# Zone name overrides (approved design names for Zorawarpur)
#
# The simulator generates "Zorawarpur Zone A" ... "Zorawarpur Zone D".
# The approved project design specifies the four names below. Overrides
# are applied at seed time only. M1 remains unchanged.
#
# Matching uses (zone_name, city_id). If this dictionary changes after
# the first successful seed, manual cleanup is required:
#     DELETE FROM zones;
# then re-seed, otherwise the seed will fail its count verification
# because old rows will no longer match.
# ----------------------------------------------------------------------

ZONE_NAME_OVERRIDES = {
    "C1-Z1": "Z-01 North Heights",
    "C1-Z2": "Z-02 Central Zora",
    "C1-Z3": "Z-03 Zora Industrial Belt",
    "C1-Z4": "Z-04 New Zora",
}


# ----------------------------------------------------------------------
# Simulator -> documented value mappings
# ----------------------------------------------------------------------

SENSOR_TYPE_BY_CLASS = {
    PressureSensor: "Pressure",
    FlowSensor: "Flow",
    LevelSensor: "Level",
    WaterTemperatureSensor: "Water Temperature",
    pHSensor: "pH",
    TurbiditySensor: "Turbidity",
    TemperatureSensor: "Equipment Condition",
    VibrationSensor: "Equipment Condition",
    PowerSensor: "Equipment Condition",
    EquipmentStatusSensor: "Equipment Condition",
    PositionSensor: "Equipment Condition",
}

ASSET_TYPE_BY_ENUM = {
    AssetType.TREATMENT_FACILITY: "TreatmentFacility",
    AssetType.RESERVOIR: "Reservoir",
    AssetType.PUMP_STATION: "PumpStation",
    AssetType.PIPELINE: "Pipeline",
    AssetType.VALVE: "Valve",
}


# ----------------------------------------------------------------------
# Return type
# ----------------------------------------------------------------------

@dataclass
class InventoryMaps:
    """In-memory identifier maps built during seeding.

    Rebuilt on every seed_inventory() call from the current database
    state. Never cached across processes.
    """

    asset_id_by_simulator_id: Dict[str, int] = field(default_factory=dict)
    sensor_id_by_simulator_id: Dict[str, int] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Public entry point
# ----------------------------------------------------------------------

def seed_inventory() -> InventoryMaps:
    """Seed or verify the complete simulator inventory in PostgreSQL.

    Steps:
        1. Verify the override dictionary (fail fast on typo).
        2. Create the virtual city and initialize its sensors.
        3. Within one transaction, match-or-insert every city, zone,
           asset, subtype row, and sensor.
        4. Verify counts, name uniqueness, and map sizes.
        5. Commit.

    Idempotent. On any failure, the transaction is rolled back and
    the exception propagates.
    """
    _verify_zone_overrides()

    virtual_city = create_virtual_city()
    initialize_sensors()

    db = SessionLocal()
    try:
        maps = _seed_all(db, virtual_city)
        _verify_counts(db)
        _verify_name_uniqueness(db)
        _verify_maps(maps)
        db.commit()
        return maps
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ----------------------------------------------------------------------
# Seeding pipeline
# ----------------------------------------------------------------------

def _seed_all(db: Session, virtual_city) -> InventoryMaps:
    """Walk the simulator inventory and match-or-insert each record."""
    maps = InventoryMaps()

    # 1. Cities (match on city_name, which is UNIQUE in the schema)
    #    Description stays NULL — not defined in the project spec.
    city_db_id_by_sim = {}
    for city in virtual_city.cities:
        db_city = _get_or_create(db, City, city_name=city.name)
        city_db_id_by_sim[city.id] = db_city.city_id

    # 2. Zones (match on zone_name + city_id)
    #    Zorawarpur zones use approved names; other cities use the
    #    simulator-generated names. Description stays NULL.
    zone_db_id_by_sim = {}
    for zone in virtual_city.zones:
        city_db_id = city_db_id_by_sim[zone.city_id]
        zone_name = ZONE_NAME_OVERRIDES.get(zone.id, zone.name)
        db_zone = _get_or_create(
            db,
            Zone,
            zone_name=zone_name,
            city_id=city_db_id,
        )
        zone_db_id_by_sim[zone.id] = db_zone.zone_id

    # 3. Assets (match on asset_name; Decision 3: parent_asset_id = NULL)
    for asset in virtual_city.assets:
        zone_db_id = zone_db_id_by_sim[asset.zone_id]
        asset_type_str = ASSET_TYPE_BY_ENUM.get(asset.asset_type)
        if asset_type_str is None:
            raise RuntimeError(
                f"Unknown AssetType: {asset.asset_type!r} "
                f"for simulator asset {asset.id}"
            )

        db_asset = _get_or_create(
            db,
            Asset,
            asset_name=asset.id,
            defaults={
                "zone_id": zone_db_id,
                "asset_type": asset_type_str,
                "status": ASSET_STATUS,
                "parent_asset_id": None,
                "updated_at": datetime.now(),
            },
        )
        maps.asset_id_by_simulator_id[asset.id] = db_asset.asset_id
        _ensure_subtype_row(db, db_asset)

    # 4. Sensors (match on sensor_name; Decision 4 handling occurs
    #    in Step 5, not here — seed only records sensor metadata)
    for asset in virtual_city.assets:
        asset_db_id = maps.asset_id_by_simulator_id[asset.id]
        for sensor in asset.sensors:
            sensor_type = SENSOR_TYPE_BY_CLASS.get(type(sensor))
            if sensor_type is None:
                raise RuntimeError(
                    f"Unknown sensor class: {type(sensor).__name__} "
                    f"on asset {asset.id}"
                )

            db_sensor = _get_or_create(
                db,
                Sensor,
                sensor_name=sensor.sensor_id,
                defaults={
                    "asset_id": asset_db_id,
                    "sensor_type": sensor_type,
                    "status": SENSOR_STATUS,
                },
            )
            maps.sensor_id_by_simulator_id[sensor.sensor_id] = (
                db_sensor.sensor_id
            )

    return maps


def _ensure_subtype_row(db: Session, db_asset: Asset) -> None:
    """Insert the correct subtype row for this asset if missing."""
    asset_type = db_asset.asset_type

    if asset_type == "TreatmentFacility":
        _get_or_create(db, TreatmentFacility, asset_id=db_asset.asset_id)
    elif asset_type == "Reservoir":
        _get_or_create(db, Reservoir, asset_id=db_asset.asset_id)
    elif asset_type == "PumpStation":
        _get_or_create(db, PumpStation, asset_id=db_asset.asset_id)
    elif asset_type == "Pipeline":
        _get_or_create(db, Pipeline, asset_id=db_asset.asset_id)
    elif asset_type == "Valve":
        _get_or_create(db, Valve, asset_id=db_asset.asset_id)
    else:
        raise RuntimeError(
            f"Unknown asset_type on DB asset {db_asset.asset_id}: "
            f"{asset_type!r}"
        )


# ----------------------------------------------------------------------
# Match-or-insert helper
# ----------------------------------------------------------------------

def _get_or_create(
    db: Session,
    model,
    defaults: Optional[dict] = None,
    **lookup,
):
    """Return the unique row matching `lookup`, or insert a new one.

    - Zero matches  -> INSERT with lookup + defaults, return new row.
    - One match     -> return it unchanged.
    - Many matches  -> raise RuntimeError (ambiguous, per Decision 5).
    """
    if defaults is None:
        defaults = {}

    existing = db.query(model).filter_by(**lookup).all()
    if len(existing) == 1:
        return existing[0]
    if len(existing) > 1:
        raise RuntimeError(
            f"Ambiguous match for {model.__name__}: "
            f"found {len(existing)} rows for {lookup}. "
            f"Refusing to pick one arbitrarily."
        )

    instance = model(**lookup, **defaults)
    db.add(instance)
    db.flush()
    return instance


# ----------------------------------------------------------------------
# Post-seed verification
# ----------------------------------------------------------------------

def _verify_counts(db: Session) -> None:
    """Assert the database contains exactly the documented inventory."""
    expected = {
        "cities": (City, 4),
        "zones": (Zone, 16),
        "assets": (Asset, 108),
        "treatment_facilities": (TreatmentFacility, 8),
        "reservoirs": (Reservoir, 8),
        "pump_stations": (PumpStation, 12),
        "pipelines": (Pipeline, 48),
        "valves": (Valve, 32),
        "sensors": (Sensor, 328),
    }

    for name, (model, count) in expected.items():
        actual = db.query(model).count()
        if actual != count:
            raise RuntimeError(
                f"Inventory mismatch: {name} expected {count}, "
                f"got {actual}"
            )


def _verify_name_uniqueness(db: Session) -> None:
    """Decision 5: verify simulator-identity columns have no duplicates."""
    dup_assets = db.execute(text(
        "SELECT asset_name, COUNT(*) AS c FROM assets "
        "GROUP BY asset_name HAVING COUNT(*) > 1"
    )).fetchall()
    if dup_assets:
        raise RuntimeError(
            f"Duplicate asset_name values detected: {dup_assets}"
        )

    dup_sensors = db.execute(text(
        "SELECT sensor_name, COUNT(*) AS c FROM sensors "
        "GROUP BY sensor_name HAVING COUNT(*) > 1"
    )).fetchall()
    if dup_sensors:
        raise RuntimeError(
            f"Duplicate sensor_name values detected: {dup_sensors}"
        )


def _verify_maps(maps: InventoryMaps) -> None:
    """Assert the returned ID maps cover the full inventory."""
    if len(maps.asset_id_by_simulator_id) != 108:
        raise RuntimeError(
            f"Expected 108 asset ID mappings, "
            f"got {len(maps.asset_id_by_simulator_id)}"
        )
    if len(maps.sensor_id_by_simulator_id) != 328:
        raise RuntimeError(
            f"Expected 328 sensor ID mappings, "
            f"got {len(maps.sensor_id_by_simulator_id)}"
        )


def _verify_zone_overrides() -> None:
    """Guardrail: assert ZONE_NAME_OVERRIDES keys match expected set.

    A typo in a zone ID key would silently fall back to the simulator's
    generic name, causing the seed to insert a fresh zone row on the
    next run instead of matching. This check catches that mistake
    before any database work happens.
    """
    expected_keys = {"C1-Z1", "C1-Z2", "C1-Z3", "C1-Z4"}
    actual_keys = set(ZONE_NAME_OVERRIDES.keys())
    if actual_keys != expected_keys:
        raise RuntimeError(
            f"ZONE_NAME_OVERRIDES keys mismatch. "
            f"Expected: {sorted(expected_keys)}, "
            f"got: {sorted(actual_keys)}"
        )


# ----------------------------------------------------------------------
# Manual run — populate the database once
# ----------------------------------------------------------------------

if __name__ == "__main__":
    maps = seed_inventory()
    print(
        f"Seeded inventory: "
        f"{len(maps.asset_id_by_simulator_id)} assets, "
        f"{len(maps.sensor_id_by_simulator_id)} sensors"
    )