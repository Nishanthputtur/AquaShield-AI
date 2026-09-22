"""
simulator.sensors package.

Sensor-level orchestration for AquaShield AI.

This package does not attach sensors or produce readings at import time.
Call the functions explicitly after the virtual city has been created:

    from simulator.sensors import initialize_sensors, generate_all_readings

    initialize_sensors()                 # attach sensors to ASSETS
    readings = generate_all_readings()   # one combined list of readings
"""

from .pressure import (
    create_pressure_sensors,
    generate_pressure_readings,
)
from .flow import (
    create_flow_sensors,
    generate_flow_readings,
)
from .equipment import (
    create_equipment_sensors,
    generate_equipment_readings,
)
from .water_quality import (
    create_water_quality_sensors,
    generate_water_quality_readings,
)


def initialize_sensors() -> list:
    """
    Attach all four sensor groups to the current ASSETS collection.

    Uses the existing idempotent create_*_sensors() functions.
    Safe to call multiple times: already-attached sensors are skipped.

    Returns a combined list of newly created sensors
    (empty list if everything was already attached).
    """
    new_sensors = []

    new_sensors.extend(create_pressure_sensors())
    new_sensors.extend(create_flow_sensors())
    new_sensors.extend(create_equipment_sensors())
    new_sensors.extend(create_water_quality_sensors())

    return new_sensors


def generate_all_readings() -> list:
    """
    Generate one combined list of readings from all four sensor groups.

    Each element is the exact reading dictionary produced by the
    corresponding sensor module:

        {
            "sensor_id": str,
            "asset_id": str,
            "parameter": str,
            "value": float | str,
            "unit": str,
            "timestamp": str
        }
    """
    readings = []

    readings.extend(generate_pressure_readings())
    readings.extend(generate_flow_readings())
    readings.extend(generate_equipment_readings())
    readings.extend(generate_water_quality_readings())

    return readings