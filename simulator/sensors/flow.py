"""
flow.py - Virtual flow sensor module for AquaShield AI.

Generates flow rate readings for:
- Treatment Facilities
- Pump Stations
- Pipelines
- Valves

Each flow sensor is attached to its corresponding asset's `sensors` list.
Normal range: 80 - 120 L/min.
"""

import random
from datetime import datetime
from simulator.city.assets import ASSETS, AssetType


class FlowSensor:
    """Simple flow rate sensor attached to an asset."""

    def __init__(self, sensor_id: str, asset_id: str, min_lpm: float, max_lpm: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_lpm = min_lpm
        self.max_lpm = max_lpm
        self.value = None
        self.unit = "L/min"

    def read(self) -> dict:
        mid = (self.min_lpm + self.max_lpm) / 2
        range_half = (self.max_lpm - self.min_lpm) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_lpm, min(self.max_lpm, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Flow Rate",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"FlowSensor({self.sensor_id}, asset={self.asset_id})"


# All asset types that need a flow sensor share the same normal range (80-120 L/min)
FLOW_RANGES = {
    AssetType.TREATMENT_FACILITY: (80.0, 120.0),
    AssetType.PUMP_STATION: (80.0, 120.0),
    AssetType.PIPELINE: (80.0, 120.0),
    AssetType.VALVE: (80.0, 120.0),
}


def create_flow_sensors() -> list:
    """
    Create flow sensors for eligible assets and attach to asset.sensors.

    Idempotent: if a flow sensor with the expected sensor_id already
    exists on the asset, it is not created or appended again.
    """
    sensors = []

    for asset_id, asset in ASSETS.items():

        # Asset.asset_type is already an AssetType enum.
        asset_type_enum = asset.asset_type

        if asset_type_enum not in FLOW_RANGES:
            continue

        min_lpm, max_lpm = FLOW_RANGES[asset_type_enum]
        sensor_id = f"{asset_id}-FLOW"

        # Skip if this flow sensor already exists on the asset.
        already_exists = any(
            getattr(existing, "sensor_id", None) == sensor_id
            for existing in asset.sensors
        )
        if already_exists:
            continue

        sensor = FlowSensor(sensor_id, asset_id, min_lpm, max_lpm)
        asset.sensors.append(sensor)
        sensors.append(sensor)

    return sensors


def generate_flow_readings() -> list:
    """Update all flow sensors and return list of reading dictionaries."""
    readings = []
    for asset in ASSETS.values():
        for sensor in asset.sensors:
            if isinstance(sensor, FlowSensor):
                readings.append(sensor.read())
    return readings


def get_flow_reading(asset_id: str) -> dict:
    """Get a fresh flow reading for a specific asset."""
    asset = ASSETS.get(asset_id)
    if not asset:
        return None
    for sensor in asset.sensors:
        if isinstance(sensor, FlowSensor):
            return sensor.read()
    return None


def get_asset_flow_sensor(asset_id: str):
    """Return the flow sensor object for a given asset, or None."""
    asset = ASSETS.get(asset_id)
    if not asset:
        return None
    for sensor in asset.sensors:
        if isinstance(sensor, FlowSensor):
            return sensor
    return None