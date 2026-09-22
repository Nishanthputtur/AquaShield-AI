"""
water_quality.py - Water quality sensors for AquaShield AI.

Generates readings for:
- Reservoirs: Water Level, Water Temperature, pH, Turbidity
- Treatment Facilities: pH, Turbidity, Water Temperature (flow already in flow.py)

Each sensor is attached to its asset's `sensors` list.
Normal ranges are documented below.
"""

import random
from datetime import datetime
from simulator.city.assets import ASSETS, AssetType


class LevelSensor:
    """Water level sensor for Reservoirs (feet)."""

    def __init__(self, sensor_id: str, asset_id: str, min_level: float, max_level: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_level = min_level
        self.max_level = max_level
        self.value = None
        self.unit = "ft"

    def read(self) -> dict:
        mid = (self.min_level + self.max_level) / 2
        range_half = (self.max_level - self.min_level) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_level, min(self.max_level, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Water Level",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"LevelSensor({self.sensor_id})"


class WaterTemperatureSensor:
    """Water temperature sensor (°C)."""

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
            "parameter": "Water Temperature",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"WaterTemperatureSensor({self.sensor_id})"


class pHSensor:
    """pH sensor (unitless, range 0-14)."""

    def __init__(self, sensor_id: str, asset_id: str, min_ph: float, max_ph: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_ph = min_ph
        self.max_ph = max_ph
        self.value = None
        self.unit = "pH"

    def read(self) -> dict:
        mid = (self.min_ph + self.max_ph) / 2
        range_half = (self.max_ph - self.min_ph) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_ph, min(self.max_ph, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "pH",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"pHSensor({self.sensor_id})"


class TurbiditySensor:
    """Turbidity sensor (NTU)."""

    def __init__(self, sensor_id: str, asset_id: str, min_turb: float, max_turb: float):
        self.sensor_id = sensor_id
        self.asset_id = asset_id
        self.min_turb = min_turb
        self.max_turb = max_turb
        self.value = None
        self.unit = "NTU"

    def read(self) -> dict:
        mid = (self.min_turb + self.max_turb) / 2
        range_half = (self.max_turb - self.min_turb) / 2
        variation = random.uniform(-range_half * 0.8, range_half * 0.8)
        self.value = mid + variation
        self.value = max(self.min_turb, min(self.max_turb, self.value))
        return {
            "sensor_id": self.sensor_id,
            "asset_id": self.asset_id,
            "parameter": "Turbidity",
            "value": round(self.value, 2),
            "unit": self.unit,
            "timestamp": datetime.now().isoformat()
        }

    def __repr__(self) -> str:
        return f"TurbiditySensor({self.sensor_id})"


# ----------------------------------------------------------------------
# Normal ranges for water quality sensors
# ----------------------------------------------------------------------
WATER_QUALITY_RANGES = {
    AssetType.RESERVOIR: {
        "level": (5.0, 15.0),               # feet
        "water_temperature": (10.0, 25.0),  # °C
        "ph": (6.5, 8.5),                   # pH
        "turbidity": (0.0, 5.0)             # NTU
    },
    AssetType.TREATMENT_FACILITY: {
        "ph": (6.5, 8.5),
        "turbidity": (0.0, 5.0),
        "water_temperature": (10.0, 25.0)
    }
}


# ----------------------------------------------------------------------
# Explicit mapping from sensor class to its frozen parameter string.
#
# Used by get_water_quality_reading() so that lookups by parameter name
# match the actual "parameter" field returned by each sensor's read().
# ----------------------------------------------------------------------
WATER_QUALITY_PARAMETER_BY_CLASS = {
    LevelSensor: "Water Level",
    WaterTemperatureSensor: "Water Temperature",
    pHSensor: "pH",
    TurbiditySensor: "Turbidity",
}

# All water quality sensor classes (used by isinstance checks).
WATER_QUALITY_SENSOR_CLASSES = tuple(WATER_QUALITY_PARAMETER_BY_CLASS.keys())


def _sensor_exists(asset, sensor_id: str) -> bool:
    """Return True if the asset already has a sensor with this sensor_id."""
    return any(
        getattr(existing, "sensor_id", None) == sensor_id
        for existing in asset.sensors
    )


def create_water_quality_sensors() -> list:
    """
    Create water quality sensors for Reservoirs and Treatment Facilities.
    Attach each sensor to its asset's `sensors` list.
    Return list of all newly created sensors.

    Idempotent: each sensor kind is checked independently against the
    asset's existing sensors before being created.
    """
    sensors = []

    for asset_id, asset in ASSETS.items():

        # Asset.asset_type is already an AssetType enum.
        asset_type_enum = asset.asset_type

        if asset_type_enum == AssetType.RESERVOIR:
            ranges = WATER_QUALITY_RANGES[AssetType.RESERVOIR]

            # Water Level
            sensor_id = f"{asset_id}-LEVEL"
            if not _sensor_exists(asset, sensor_id):
                min_l, max_l = ranges["level"]
                level_sensor = LevelSensor(sensor_id, asset_id, min_l, max_l)
                asset.sensors.append(level_sensor)
                sensors.append(level_sensor)

            # Water Temperature
            sensor_id = f"{asset_id}-WATER-TEMP"
            if not _sensor_exists(asset, sensor_id):
                min_t, max_t = ranges["water_temperature"]
                temp_sensor = WaterTemperatureSensor(sensor_id, asset_id, min_t, max_t)
                asset.sensors.append(temp_sensor)
                sensors.append(temp_sensor)

            # pH
            sensor_id = f"{asset_id}-PH"
            if not _sensor_exists(asset, sensor_id):
                min_p, max_p = ranges["ph"]
                ph_sensor = pHSensor(sensor_id, asset_id, min_p, max_p)
                asset.sensors.append(ph_sensor)
                sensors.append(ph_sensor)

            # Turbidity
            sensor_id = f"{asset_id}-TURBIDITY"
            if not _sensor_exists(asset, sensor_id):
                min_tr, max_tr = ranges["turbidity"]
                turb_sensor = TurbiditySensor(sensor_id, asset_id, min_tr, max_tr)
                asset.sensors.append(turb_sensor)
                sensors.append(turb_sensor)

        elif asset_type_enum == AssetType.TREATMENT_FACILITY:
            ranges = WATER_QUALITY_RANGES[AssetType.TREATMENT_FACILITY]

            # pH
            sensor_id = f"{asset_id}-PH"
            if not _sensor_exists(asset, sensor_id):
                min_p, max_p = ranges["ph"]
                ph_sensor = pHSensor(sensor_id, asset_id, min_p, max_p)
                asset.sensors.append(ph_sensor)
                sensors.append(ph_sensor)

            # Turbidity
            sensor_id = f"{asset_id}-TURBIDITY"
            if not _sensor_exists(asset, sensor_id):
                min_tr, max_tr = ranges["turbidity"]
                turb_sensor = TurbiditySensor(sensor_id, asset_id, min_tr, max_tr)
                asset.sensors.append(turb_sensor)
                sensors.append(turb_sensor)

            # Water Temperature
            sensor_id = f"{asset_id}-WATER-TEMP"
            if not _sensor_exists(asset, sensor_id):
                min_t, max_t = ranges["water_temperature"]
                temp_sensor = WaterTemperatureSensor(sensor_id, asset_id, min_t, max_t)
                asset.sensors.append(temp_sensor)
                sensors.append(temp_sensor)

    return sensors


def generate_water_quality_readings() -> list:
    """Update all water quality sensors and return list of reading dictionaries."""
    readings = []
    for asset in ASSETS.values():
        for sensor in asset.sensors:
            if isinstance(sensor, WATER_QUALITY_SENSOR_CLASSES):
                readings.append(sensor.read())
    return readings


def get_water_quality_reading(asset_id: str, parameter: str = None) -> dict or list: # type: ignore
    """
    Get a fresh reading for a specific asset.

    If parameter is given (exact frozen parameter name such as
    'Water Level', 'Water Temperature', 'pH', 'Turbidity'),
    return that reading.
    Otherwise return a list of all water quality readings for that asset.
    """
    asset = ASSETS.get(asset_id)
    if not asset:
        return None

    results = []
    for sensor in asset.sensors:
        if not isinstance(sensor, WATER_QUALITY_SENSOR_CLASSES):
            continue

        param_name = WATER_QUALITY_PARAMETER_BY_CLASS.get(type(sensor))

        if parameter is None or param_name == parameter:
            results.append(sensor.read())

    if parameter:
        return results[0] if results else None
    return results if results else None


def get_asset_water_quality_sensors(asset_id: str) -> list:
    """Return a list of all water quality sensor objects for a given asset."""
    asset = ASSETS.get(asset_id)
    if not asset:
        return []
    return [
        s for s in asset.sensors
        if isinstance(s, WATER_QUALITY_SENSOR_CLASSES)
    ]