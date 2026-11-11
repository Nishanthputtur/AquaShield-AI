"""
Sensor reading persistence and reconstruction for AquaShield AI.

This module is the bridge between the simulator's six-field reading
dicts and the database's sensor_readings table.

Persistence (simulator -> database)
-----------------------------------
The simulator produces:

    {
        "sensor_id": "C1-P-001-PRESSURE",   # simulator sensor ID
        "asset_id": "C1-P-001",             # simulator asset ID
        "parameter": "Pressure",
        "value": 52.3,
        "unit": "PSI",
        "timestamp": "2024-01-01T00:00:00"  # ISO string
    }

This module:
    1. Resolves `sensor_id` to the DB `sensors.sensor_id` via
       `sensors.sensor_name`.
    2. Resolves the column by parameter type (Decision 4):
        - non-equipment numeric -> reading_value_numeric
        - equipment (all 5 types) -> reading_value_text
    3. Converts the ISO timestamp to a datetime.
    4. Creates the sensor_readings row.

Reconstruction (database -> simulator)
--------------------------------------
The database stores integer FKs and two value columns. To rebuild the
original six-field dict, this module:
    1. Joins sensor_readings -> sensors -> assets
    2. Recovers simulator sensor_id from sensors.sensor_name
    3. Recovers simulator asset_id from assets.asset_name
    4. Looks up the simulator sensor object in ASSETS
    5. Recovers parameter from the sensor class (via mapping table)
    6. Recovers unit from sensor.unit
    7. If reading_value_numeric is set, returns float
    8. If reading_value_text is set:
        - Equipment Status parameter -> return text unchanged
        - Other numeric equipment parameter -> parse to float

Assumptions
-----------
- Caller must have called create_virtual_city() and initialize_sensors()
  before calling any function in this module. This module does not
  auto-initialize the simulator.
- The simulator is frozen (M1). The parameter mapping below must match
  the exact parameter strings emitted by each sensor class.
"""

from datetime import datetime
from typing import Dict, List

from sqlalchemy.orm import Session

from backend.app.models import Asset, Sensor, SensorReading
from simulator.city.assets import ASSETS
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
# Parameter mapping — must match the simulator's read() output exactly.
#
# Class names verified against the simulator source. Parameter strings
# verified against each class's read() return value. The "Valve Position"
# string is the actual parameter emitted by PositionSensor (not "Position").
# ----------------------------------------------------------------------

PARAMETER_BY_CLASS = {
    PressureSensor: "Pressure",
    FlowSensor: "Flow Rate",
    LevelSensor: "Water Level",
    WaterTemperatureSensor: "Water Temperature",
    pHSensor: "pH",
    TurbiditySensor: "Turbidity",
    TemperatureSensor: "Temperature",
    VibrationSensor: "Vibration",
    PowerSensor: "Power Consumption",
    EquipmentStatusSensor: "Equipment Status",
    PositionSensor: "Valve Position",
}

# Decision 4: these equipment parameters are stored as text in the DB
# but must be parsed back to float during reconstruction.
NUMERIC_EQUIPMENT_PARAMETERS = {
    "Temperature",
    "Vibration",
    "Power Consumption",
    "Valve Position",
}

# Decision 4: this equipment parameter is genuinely text.
TEXT_EQUIPMENT_PARAMETERS = {
    "Equipment Status",
}


# ----------------------------------------------------------------------
# Persistence
# ----------------------------------------------------------------------

def persist_readings(
    db: Session,
    readings: List[Dict],
) -> int:
    """Persist a batch of simulator readings to the sensor_readings table.

    The caller must have already called initialize_sensors(). The function
    assumes ASSETS is populated with sensor objects.

    Arguments:
        db: Active SQLAlchemy session. The caller controls commit/rollback.
        readings: List of six-field reading dicts from the simulator.

    Returns:
        The number of rows inserted.

    Raises:
        ValueError: if a reading is malformed or references a sensor
            that cannot be resolved to a database row.
    """
    if not readings:
        return 0

    # Bulk-resolve sensor_name -> sensor_id to avoid N+1 queries.
    sensor_names = {r["sensor_id"] for r in readings}
    sensor_rows = (
        db.query(Sensor)
        .filter(Sensor.sensor_name.in_(sensor_names))
        .all()
    )
    sensor_id_by_name = {s.sensor_name: s.sensor_id for s in sensor_rows}

    missing = sensor_names - set(sensor_id_by_name.keys())
    if missing:
        raise ValueError(
            f"Cannot resolve simulator sensor IDs to database sensors. "
            f"Missing: {sorted(missing)[:5]}"
            f"{' ...' if len(missing) > 5 else ''}. "
            f"Has seed_inventory() been run?"
        )

    rows = []
    for reading in readings:
        db_sensor_id = sensor_id_by_name[reading["sensor_id"]]
        parameter = reading["parameter"]

        # Decision 4: choose column by parameter type.
        if parameter in TEXT_EQUIPMENT_PARAMETERS:
            value_numeric = None
            value_text = str(reading["value"])
        elif parameter in NUMERIC_EQUIPMENT_PARAMETERS:
            value_numeric = None
            value_text = str(reading["value"])
        else:
            # Non-equipment numeric parameter.
            value_numeric = float(reading["value"])
            value_text = None

        # Simulator emits ISO string; DB column is DateTime.
        timestamp = datetime.fromisoformat(reading["timestamp"])

        rows.append(SensorReading(
            sensor_id=db_sensor_id,
            reading_value_numeric=value_numeric,
            reading_value_text=value_text,
            timestamp=timestamp,
            status=None,
        ))

    db.add_all(rows)
    db.flush()
    return len(rows)


# ----------------------------------------------------------------------
# Reconstruction
# ----------------------------------------------------------------------

def reconstruct_reading(
    reading_row: SensorReading,
    sensor_row: Sensor,
    asset_row: Asset,
) -> Dict:
    """Rebuild the original six-field simulator reading from DB rows.

    Arguments:
        reading_row: SensorReading ORM row.
        sensor_row:  Sensor ORM row joined to reading_row.
        asset_row:   Asset ORM row joined to sensor_row.

    Returns:
        A dict with keys: sensor_id, asset_id, parameter, value, unit,
        timestamp. `value` is float for numeric readings, str for
        Equipment Status.
    """
    simulator_sensor_id = sensor_row.sensor_name   # simulator sensor ID
    simulator_asset_id = asset_row.asset_name      # simulator asset ID

    simulator_sensor = _find_simulator_sensor(
        simulator_asset_id, simulator_sensor_id
    )
    parameter = PARAMETER_BY_CLASS.get(type(simulator_sensor))
    if parameter is None:
        raise RuntimeError(
            f"Unknown simulator sensor class: "
            f"{type(simulator_sensor).__name__}"
        )
    unit = simulator_sensor.unit

    # Decision 4: reconstruct numeric vs text based on parameter type.
    if reading_row.reading_value_numeric is not None:
        value = float(reading_row.reading_value_numeric)
    else:
        text_value = reading_row.reading_value_text
        if parameter in NUMERIC_EQUIPMENT_PARAMETERS:
            try:
                value = float(text_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Cannot parse equipment numeric value "
                    f"{text_value!r} for parameter {parameter!r}"
                ) from exc
        elif parameter in TEXT_EQUIPMENT_PARAMETERS:
            value = text_value
        else:
            raise ValueError(
                f"Reading has neither numeric nor text value "
                f"(reading_id={reading_row.reading_id})"
            )

    return {
        "sensor_id": simulator_sensor_id,
        "asset_id": simulator_asset_id,
        "parameter": parameter,
        "value": value,
        "unit": unit,
        "timestamp": reading_row.timestamp.isoformat(),
    }


def get_recent_readings(
    db: Session,
    limit: int = 100,
) -> List[Dict]:
    """Return the most recent readings, reconstructed to simulator format.

    Arguments:
        db: Active SQLAlchemy session.
        limit: Maximum number of readings to return, ordered by most
            recent first.

    Returns:
        List of six-field dicts in simulator format.
    """
    rows = (
        db.query(SensorReading, Sensor, Asset)
        .join(Sensor, SensorReading.sensor_id == Sensor.sensor_id)
        .join(Asset, Sensor.asset_id == Asset.asset_id)
        .order_by(SensorReading.timestamp.desc())
        .limit(limit)
        .all()
    )

    return [
        reconstruct_reading(reading, sensor, asset)
        for reading, sensor, asset in rows
    ]


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------

def _find_simulator_sensor(asset_id: str, sensor_id: str):
    """Locate the simulator sensor object for the given IDs.

    Raises ValueError with a clear message if ASSETS is not populated
    or the sensor is not attached.
    """
    if not ASSETS:
        raise ValueError(
            "ASSETS is empty. Call create_virtual_city() and "
            "initialize_sensors() before using monitoring_service."
        )

    asset = ASSETS.get(asset_id)
    if asset is None:
        raise ValueError(
            f"Simulator asset not found in ASSETS: {asset_id!r}"
        )

    for sensor in asset.sensors:
        if sensor.sensor_id == sensor_id:
            return sensor

    raise ValueError(
        f"Simulator sensor not found on {asset_id!r}: {sensor_id!r}"
    )