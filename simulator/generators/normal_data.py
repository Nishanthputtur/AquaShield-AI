"""Baseline reading generator for the AquaShield AI simulator.

This module produces the "normal" baseline readings that the event
layer later modifies. It never applies events, never scores readings,
and never persists anything.

It is a thin wrapper over the adapter in sensor_data.py:

    ensure_sensors_initialized()
        -> sensor_data.initialize_sensors()   (idempotent)

    get_normal_readings()
        -> ensure_sensors_initialized()
        -> sensor_data.generate_all_readings()
        -> list[dict] with the frozen reading schema

Callers must create the virtual city before calling these functions,
so that ASSETS is populated with the 108 assets.

Importing this module performs no work. No sensors are initialized,
no readings are generated, and no state is created.
"""

from simulator.generators.sensor_data import (
    SensorReading,
    generate_all_readings,
    initialize_sensors,
)


def ensure_sensors_initialized() -> None:
    """Ensure virtual sensors are attached to all city assets.

    Delegates to the sensor adapter, which is idempotent: repeated
    calls do not attach duplicate sensors.

    The caller must have already created the virtual city so that
    ASSETS contains the 108 assets. If ASSETS is empty, this call
    attaches no sensors and subsequent reading generation returns
    an empty list.
    """
    initialize_sensors()


def get_normal_readings() -> list[SensorReading]:
    """Return one baseline reading cycle for the current virtual city.

    Steps:
        1. Ensure sensors are initialized (idempotent).
        2. Generate one combined reading cycle from all sensors.

    No events are applied. No analytics are performed. No persistence
    occurs. The returned list has exactly 328 readings (one per sensor)
    across the 108 assets of the current virtual city, each with the
    frozen schema:

        {
            "sensor_id": str,
            "asset_id": str,
            "parameter": str,
            "value": float | str,
            "unit": str,
            "timestamp": str
        }
    """
    ensure_sensors_initialized()
    return generate_all_readings()