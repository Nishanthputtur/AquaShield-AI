"""
equipment.py - Virtual equipment sensors for AquaShield AI.

Generates equipment-related readings for:
- Pump Stations: Temperature, Vibration, Power Consumption, Equipment Status
- Valves: Valve Position

Each sensor is attached to its asset's `sensors` list.
Normal operating ranges are documented below.
"""

import random
from datetime import datetime
from simulator.city.assets import ASSETS, AssetType


class TemperatureSensor:
    """Temperature sensor for Pump Stations (°C)."""

    def __init__(self, sensor_id: str, asset_id: str, min_temp: float, max_temp: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.value = None
        self.unit = "°C"

    def read(self) -> dict:
        mid = (self.min_temp + self.max_temp) / 2
        range_half = (self.max_temp - self.min_temp) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_temp, min(self.max_temp, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Temperature",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"TemperatureSensor({self.sensor_id})"


class VibrationSensor:
    """Vibration sensor for Pump Stations (mm/s)."""

    def __init__(self, sensor_id: str, asset_id: str, min_vib: float, max_vib: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_vib = min_vib
        self.max_vib = max_vib
        self.value = None
        self.unit = "mm/s"

    def read(self) -> dict:
        mid = (self.min_vib + self.max_vib) / 2
        range_half = (self.max_vib - self.min_vib) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_vib, min(self.max_vib, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Vibration",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"VibrationSensor({self.sensor_id})"


class PowerSensor:
    """Power consumption sensor for Pump Stations (kW)."""

    def __init__(self, sensor_id: str, asset_id: str, min_power: float, max_power: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_power = min_power
        self.max_power = max_power
        self.value = None
        self.unit = "kW"

    def read(self) -> dict:
        mid = (self.min_power + self.max_power) / 2
        range_half = (self.max_power - self.min_power) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_power, min(self.max_power, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Power Consumption",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"PowerSensor({self.sensor_id})"


class EquipmentStatusSensor:
    """Equipment status sensor for Pump Stations."""

    # Possible statuses (normal operation)
    STATUSES = ["ON", "OFF", "STANDBY"]

    def __init__(self, sensor_id: str, asset_id: str):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.value = None
        self.unit = "STATUS"

    def read(self) -> dict:
        # Bias towards "ON" (70% chance) to represent normal operation
        if random.random() < 0.70:
            self.value = "ON"
        else:
            self.value = random.choice(["OFF", "STANDBY"])
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Equipment Status",
            "value": self.value,
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"EquipmentStatusSensor({self.sensor_id})"


class PositionSensor:
    """Valve position sensor (0–100% open)."""

    def __init__(self, sensor_id: str, asset_id: str, min_pos: float, max_pos: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_pos = min_pos
        self.max_pos = max_pos
        self.value = None
        self.unit = "%"

    def read(self) -> dict:
        mid = (self.min_pos + self.max_pos) / 2
        range_half = (self.max_pos - self.min_pos) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_pos, min(self.max_pos, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Valve Position",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"PositionSensor({self.sensor_id})"


# ----------------------------------------------------------------------
# Normal ranges for equipment sensors
# ----------------------------------------------------------------------
EQUIPMENT_RANGES = {
    AssetType.PUMP_STATION: {
        "temperature": (20.0, 40.0),      # °C
        "vibration": (0.0, 5.0),          # mm/s
        "power": (10.0, 50.0),            # kW
        "status": None                    # handled separately
    },
    AssetType.VALVE: {
        "position": (20.0, 80.0)          # % open (normal operating range)
    }
}


# ----------------------------------------------------------------------
# Explicit mapping from sensor class to its frozen parameter string.
#
# This is used by get_equipment_reading() so that lookups by parameter
# name match the actual "parameter" field returned by each sensor's read().
# ----------------------------------------------------------------------
EQUIPMENT_PARAMETER_BY_CLASS = {
    TemperatureSensor: "Temperature",
    VibrationSensor: "Vibration",
    PowerSensor: "Power Consumption",
    EquipmentStatusSensor: "Equipment Status",
    PositionSensor: "Valve Position",
}

# All equipment sensor classes (used by isinstance checks).
EQUIPMENT_SENSOR_CLASSES = tuple(EQUIPMENT_PARAMETER_BY_CLASS.keys())


def _sensor_exists(asset, sensor_id: str) -> bool:
    """Return True if the asset already has a sensor with this sensor_id."""
    return any(
        getattr(existing, "sensor_id", None) == sensor_id
        for existing in asset.sensors
    )


def create_equipment_sensors() -> list:
    """
    Create equipment sensors for Pump Stations and Valves.
    Attach each sensor to its asset's `sensors` list.
    Return list of all newly created sensors.

    Idempotent: each sensor kind is checked independently against the
    asset's existing sensors before being created.
    """
    sensors = []

    for asset_id, asset in ASSETS.items():

        # Asset.asset_type is already an AssetType enum.
        asset_type_enum = asset.asset_type

        if asset_type_enum == AssetType.PUMP_STATION:
            # Temperature
            sensor_id = f"{asset_id}-TEMPERATURE"
            if not _sensor_exists(asset, sensor_id):
                min_t, max_t = EQUIPMENT_RANGES[AssetType.PUMP_STATION]["temperature"]
                temp_sensor = TemperatureSensor(sensor_id, asset_id, min_t, max_t)
                asset.sensors.append(temp_sensor)
                sensors.append(temp_sensor)

            # Vibration
            sensor_id = f"{asset_id}-VIBRATION"
            if not _sensor_exists(asset, sensor_id):
                min_v, max_v = EQUIPMENT_RANGES[AssetType.PUMP_STATION]["vibration"]
                vib_sensor = VibrationSensor(sensor_id, asset_id, min_v, max_v)
                asset.sensors.append(vib_sensor)
                sensors.append(vib_sensor)

            # Power
            sensor_id = f"{asset_id}-POWER"
            if not _sensor_exists(asset, sensor_id):
                min_p, max_p = EQUIPMENT_RANGES[AssetType.PUMP_STATION]["power"]
                power_sensor = PowerSensor(sensor_id, asset_id, min_p, max_p)
                asset.sensors.append(power_sensor)
                sensors.append(power_sensor)

            # Equipment Status
            sensor_id = f"{asset_id}-EQUIPMENT-STATUS"
            if not _sensor_exists(asset, sensor_id):
                status_sensor = EquipmentStatusSensor(sensor_id, asset_id)
                asset.sensors.append(status_sensor)
                sensors.append(status_sensor)

        elif asset_type_enum == AssetType.VALVE:
            # Valve Position
            sensor_id = f"{asset_id}-POSITION"
            if not _sensor_exists(asset, sensor_id):
                min_pos, max_pos = EQUIPMENT_RANGES[AssetType.VALVE]["position"]
                pos_sensor = PositionSensor(sensor_id, asset_id, min_pos, max_pos)
                asset.sensors.append(pos_sensor)
                sensors.append(pos_sensor)

    return sensors


def generate_equipment_readings() -> list:
    """Update all equipment sensors and return list of reading dictionaries."""
    readings = []
    for asset in ASSETS.values():
        for sensor in asset.sensors:
            if isinstance(sensor, EQUIPMENT_SENSOR_CLASSES):
                readings.append(sensor.read())
    return readings


def get_equipment_reading(asset_id: str, parameter: str = None) -> dict or list: # type: ignore
    """
    Get a fresh reading for a specific asset.

    If parameter is given (exact frozen parameter name such as
    'Temperature', 'Vibration', 'Power Consumption',
    'Equipment Status', 'Valve Position'), return that reading.
    Otherwise return a list of all equipment readings for that asset.
    """
    asset = ASSETS.get(asset_id)
    if not asset:
        return None

    results = []
    for sensor in asset.sensors:
        if not isinstance(sensor, EQUIPMENT_SENSOR_CLASSES):
            continue

        param_name = EQUIPMENT_PARAMETER_BY_CLASS.get(type(sensor))

        if parameter is None or param_name == parameter:
            results.append(sensor.read())

    if parameter:
        return results[0] if results else None
    return results if results else None


def get_asset_equipment_sensors(asset_id: str) -> list:
    """Return a list of all equipment sensor objects for a given asset."""
    asset = ASSETS.get(asset_id)
    if not asset:
        return []
    return [
        s for s in asset.sensors
        if isinstance(s, EQUIPMENT_SENSOR_CLASSES)
    ]