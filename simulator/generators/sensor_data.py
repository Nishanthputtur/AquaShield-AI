"""Adapter functions for the existing virtual sensor package.

The Virtual Water City must be created before sensor initialization.
Importing this module does not initialize sensors or generate readings.

This module is a thin wrapper. It exists so that the rest of the
generator layer can depend on a single stable import path, without
reaching into simulator.sensors directly. It performs no event
processing, no scoring, and no state management.

Flow:
    simulator.sensors.initialize_sensors()
        -> simulator.sensors.generate_all_readings()
        -> list[dict] with the frozen reading schema
"""

from typing import TypeAlias

from simulator.sensors import (
    generate_all_readings as _generate_all_readings,
    initialize_sensors as _initialize_sensors,
)


# Frozen reading schema used throughout the simulator.
#
#   {
#       "sensor_id": str,
#       "asset_id": str,
#       "parameter": str,
#       "value": float | str,
#       "unit": str,
#       "timestamp": str
#   }
SensorReading: TypeAlias = dict[str, str | float]


def initialize_sensors() -> None:
    """Initialize virtual sensors for the existing city assets.

    The caller must have already created the virtual city (for example,
    by calling create_virtual_city()) so that ASSETS is populated.

    This function is idempotent: calling it repeatedly does not attach
    duplicate sensors. It does not create cities, assets, or sensors
    from scratch; it only attaches sensors to already-existing assets.
    """
    _initialize_sensors()


def generate_all_readings() -> list[SensorReading]:
    """Generate one combined list of readings from all attached sensors.

    Each reading has the frozen schema:

        {
            "sensor_id": str,
            "asset_id": str,
            "parameter": str,
            "value": float | str,
            "unit": str,
            "timestamp": str
        }

    Sensors must already be initialized before calling this function.
    A normal generation cycle returns exactly 328 readings across the
    108 assets of the current virtual city.
    """
    return _generate_all_readings()