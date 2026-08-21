"""
pressure.py - Virtual pressure sensor module for AquaShield AI.
"""

import random
from datetime import datetime
from simulator.city.assets import ASSETS, AssetType


class PressureSensor:
    """Simple pressure sensor attached to an asset."""

    def __init__(self, sensor_id: str, asset_id: str, min_psi: float, max_psi: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_psi = min_psi
        self.max_psi = max_psi
        self.value = None
        self.unit = "PSI"

    def read(self) -> dict:
        mid = (self.min_psi + self.max_psi) / 2
        range_half = (self.max_psi - self.min_psi) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_psi, min(self.max_psi, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Pressure",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"PressureSensor({self.sensor_id}, asset={self.asset_id})"


# Pressure ranges per asset type (keyed by enum member)
PRESSURE_RANGES = {
    AssetType.PIPELINE: (40.0, 60.0),
    AssetType.PUMP_STATION: (60.0, 80.0),
    AssetType.VALVE: (40.0, 60.0),
}


def create_pressure_sensors() -> list:
    sensors = []
    for asset_id, asset in ASSETS.items():
        try:
            # Convert string to enum member
            asset_type_enum = AssetType(asset.asset_type)
        except ValueError:
            continue  # should not happen with valid assets
        if asset_type_enum not in PRESSURE_RANGES:
            continue
        min_psi, max_psi = PRESSURE_RANGES[asset_type_enum]
        sensor_id = f"{asset_id}-PRESSURE"
        sensor = PressureSensor(sensor_id, asset_id, min_psi, max_psi)
        asset.sensors.append(sensor)
        sensors.append(sensor)
    return sensors


def generate_pressure_readings() -> list:
    readings = []
    for asset in ASSETS.values():
        for sensor in asset.sensors:
            if isinstance(sensor, PressureSensor):
                readings.append(sensor.read())
    return readings


def get_pressure_reading(asset_id: str) -> dict:
    asset = ASSETS.get(asset_id)
    if not asset:
        return None
    for sensor in asset.sensors:
        if isinstance(sensor, PressureSensor):
            return sensor.read()
    return None


def get_asset_pressure_sensor(asset_id: str):
    asset = ASSETS.get(asset_id)
    if not asset:
        return None
    for sensor in asset.sensors:
        if isinstance(sensor, PressureSensor):
            return sensor
    return None