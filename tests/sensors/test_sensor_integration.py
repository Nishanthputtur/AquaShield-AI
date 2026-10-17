"""
Integration test for the completed AquaShield AI city and sensor layers.

Run from the project root:

    pytest tests/sensors/test_sensor_integration.py -v

The test exercises the full pipeline:

    create_virtual_city()
        -> ASSETS populated with the same Asset objects
        -> initialize_sensors() attaches sensors to asset.sensors
        -> generate_all_readings() produces the frozen reading dicts

No production code is modified by this test.
"""

import pytest

from simulator.city.assets import ASSETS, AssetType
from simulator.city.virtual_city import create_virtual_city

from simulator.sensors import initialize_sensors, generate_all_readings
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
# Expected constants
# ----------------------------------------------------------------------

FROZEN_CITY_NAMES = ["Zorawarpur", "Amaranagar", "Rajatgiri", "Rajatpur"]

EXPECTED_CITIES = 4
EXPECTED_ZONES = 16
EXPECTED_ASSETS = 108

EXPECTED_PRESSURE_SENSORS = 92
EXPECTED_FLOW_SENSORS = 100
EXPECTED_EQUIPMENT_SENSORS = 80
EXPECTED_WATER_QUALITY_SENSORS = 56
EXPECTED_TOTAL_SENSORS = 328

SENSORS_PER_ASSET_TYPE = {
    AssetType.TREATMENT_FACILITY: 4,
    AssetType.RESERVOIR: 4,
    AssetType.PUMP_STATION: 6,
    AssetType.PIPELINE: 2,
    AssetType.VALVE: 3,
}

EXPECTED_PARAMETERS_BY_TYPE = {
    AssetType.TREATMENT_FACILITY: {
        "Flow Rate", "pH", "Turbidity", "Water Temperature",
    },
    AssetType.RESERVOIR: {
        "Water Level", "Water Temperature", "pH", "Turbidity",
    },
    AssetType.PUMP_STATION: {
        "Pressure", "Flow Rate", "Temperature", "Vibration",
        "Power Consumption", "Equipment Status",
    },
    AssetType.PIPELINE: {
        "Pressure", "Flow Rate",
    },
    AssetType.VALVE: {
        "Pressure", "Flow Rate", "Valve Position",
    },
}

ALL_PARAMETERS = {
    "Temperature",
    "Vibration",
    "Power Consumption",
    "Equipment Status",
    "Valve Position",
    "Flow Rate",
    "Pressure",
    "Water Level",
    "Water Temperature",
    "pH",
    "Turbidity",
}

EQUIPMENT_STATUS_VALUES = {"ON", "OFF", "STANDBY"}

READING_KEYS = {
    "sensor_id",
    "asset_id",
    "parameter",
    "value",
    "unit",
    "timestamp",
}


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _sensor_parameter(sensor):
    """
    Return the frozen parameter string for a given sensor instance.

    Mirrors exactly what each sensor's read() puts in the "parameter"
    field. Used to verify per-asset parameter sets without relying on
    reading generation randomness.
    """
    if isinstance(sensor, PressureSensor):
        return "Pressure"
    if isinstance(sensor, FlowSensor):
        return "Flow Rate"
    if isinstance(sensor, TemperatureSensor):
        return "Temperature"
    if isinstance(sensor, VibrationSensor):
        return "Vibration"
    if isinstance(sensor, PowerSensor):
        return "Power Consumption"
    if isinstance(sensor, EquipmentStatusSensor):
        return "Equipment Status"
    if isinstance(sensor, PositionSensor):
        return "Valve Position"
    if isinstance(sensor, LevelSensor):
        return "Water Level"
    if isinstance(sensor, WaterTemperatureSensor):
        return "Water Temperature"
    if isinstance(sensor, pHSensor):
        return "pH"
    if isinstance(sensor, TurbiditySensor):
        return "Turbidity"
    return None


def _count_sensors_by_family(virtual_city):
    """Return (pressure, flow, equipment, water_quality, total) counts."""
    pressure = 0
    flow = 0
    equipment = 0
    water_quality = 0
    total = 0

    for asset in virtual_city.assets:
        for sensor in asset.sensors:
            total += 1
            if isinstance(sensor, PressureSensor):
                pressure += 1
            elif isinstance(sensor, FlowSensor):
                flow += 1
            elif isinstance(sensor, (
                TemperatureSensor,
                VibrationSensor,
                PowerSensor,
                EquipmentStatusSensor,
                PositionSensor,
            )):
                equipment += 1
            elif isinstance(sensor, (
                LevelSensor,
                WaterTemperatureSensor,
                pHSensor,
                TurbiditySensor,
            )):
                water_quality += 1

    return pressure, flow, equipment, water_quality, total


# ----------------------------------------------------------------------
# Fixture
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def virtual_city():
    """
    Create the virtual city once for this module.

    Sensors are NOT attached here. Tests call initialize_sensors()
    themselves as needed. That function is idempotent.
    """
    return create_virtual_city()


# ----------------------------------------------------------------------
# 1 and 2: Virtual city creation and frozen city names
# ----------------------------------------------------------------------

def test_virtual_city_creation(virtual_city):
    """The virtual city must contain exactly 4 cities, 16 zones, 108 assets."""
    assert len(virtual_city.cities) == EXPECTED_CITIES
    assert len(virtual_city.zones) == EXPECTED_ZONES
    assert len(virtual_city.assets) == EXPECTED_ASSETS


def test_frozen_city_names(virtual_city):
    """City names must match the frozen AquaShield AI specification."""
    names = [city.name for city in virtual_city.cities]
    assert names == FROZEN_CITY_NAMES


# ----------------------------------------------------------------------
# 3: ASSETS registry identity
# ----------------------------------------------------------------------

def test_assets_registry_size(virtual_city):
    assert len(ASSETS) == EXPECTED_ASSETS


def test_assets_registry_identity(virtual_city):
    """ASSETS must reference the exact same Asset objects as VirtualCity."""
    for asset in virtual_city.assets:
        assert asset.id in ASSETS
        assert ASSETS[asset.id] is asset


# ----------------------------------------------------------------------
# 4: Sensor lists start empty
# ----------------------------------------------------------------------

def test_sensor_lists_start_empty(virtual_city):
    """
    Every asset must expose an empty sensors list before initialization.

    This test is defined before any test that calls initialize_sensors()
    so it runs on the freshly created virtual city.
    """
    for asset in virtual_city.assets:
        assert isinstance(asset.sensors, list)
        assert asset.sensors == [], (
            f"Asset {asset.id} has sensors before initialization."
        )


# ----------------------------------------------------------------------
# 5, 6, 7: Sensor initialization, distribution, ID uniqueness
# ----------------------------------------------------------------------

def test_initialize_sensors_counts(virtual_city):
    """Sensor families must match the expected counts and total."""
    initialize_sensors()

    pressure, flow, equipment, water_quality, total = _count_sensors_by_family(
        virtual_city
    )

    assert pressure == EXPECTED_PRESSURE_SENSORS
    assert flow == EXPECTED_FLOW_SENSORS
    assert equipment == EXPECTED_EQUIPMENT_SENSORS
    assert water_quality == EXPECTED_WATER_QUALITY_SENSORS
    assert total == EXPECTED_TOTAL_SENSORS


def test_sensor_distribution_per_asset_type(virtual_city):
    """Each asset must carry exactly the expected number of sensors."""
    initialize_sensors()

    for asset in virtual_city.assets:
        expected_count = SENSORS_PER_ASSET_TYPE[asset.asset_type]
        assert len(asset.sensors) == expected_count, (
            f"{asset.id} ({asset.asset_type.value}) has "
            f"{len(asset.sensors)} sensors, expected {expected_count}."
        )


def test_sensor_parameters_match_asset_type(virtual_city):
    """Each asset's sensor parameters must match its frozen expected set."""
    initialize_sensors()

    for asset in virtual_city.assets:
        expected_params = EXPECTED_PARAMETERS_BY_TYPE[asset.asset_type]
        actual_params = {
            _sensor_parameter(sensor)
            for sensor in asset.sensors
        }
        assert actual_params == expected_params, (
            f"{asset.id} ({asset.asset_type.value}) has parameters "
            f"{actual_params}, expected {expected_params}."
        )


def test_sensor_ids_unique_and_correct(virtual_city):
    """Sensor IDs must be unique and tied to the owning asset."""
    initialize_sensors()

    seen_ids = set()

    for asset in virtual_city.assets:
        for sensor in asset.sensors:
            assert sensor.sensor_id not in seen_ids, (
                f"Duplicate sensor_id: {sensor.sensor_id}"
            )
            seen_ids.add(sensor.sensor_id)

            assert sensor.asset_id == asset.id
            assert sensor.sensor_id.startswith(asset.id + "-"), (
                f"Sensor {sensor.sensor_id} does not belong to {asset.id}."
            )

    assert len(seen_ids) == EXPECTED_TOTAL_SENSORS


# ----------------------------------------------------------------------
# 8: Idempotent initialization
# ----------------------------------------------------------------------

def test_idempotent_initialization(virtual_city):
    """Calling initialize_sensors() twice must not attach new sensors."""
    initialize_sensors()  # ensure attached; idempotent

    before = sum(len(asset.sensors) for asset in virtual_city.assets)
    assert before == EXPECTED_TOTAL_SENSORS

    newly_created = initialize_sensors()  # second call
    after = sum(len(asset.sensors) for asset in virtual_city.assets)

    assert newly_created == []
    assert after == EXPECTED_TOTAL_SENSORS

    for asset in virtual_city.assets:
        expected_count = SENSORS_PER_ASSET_TYPE[asset.asset_type]
        assert len(asset.sensors) == expected_count


# ----------------------------------------------------------------------
# 9, 10, 11: Reading generation
# ----------------------------------------------------------------------

def test_generate_all_readings_count_and_schema(virtual_city):
    initialize_sensors()

    readings = generate_all_readings()

    assert isinstance(readings, list)
    assert len(readings) == EXPECTED_TOTAL_SENSORS

    for reading in readings:
        assert set(reading.keys()) == READING_KEYS


def test_generate_all_readings_parameter_names(virtual_city):
    initialize_sensors()

    readings = generate_all_readings()

    for reading in readings:
        assert reading["parameter"] in ALL_PARAMETERS


def test_generate_all_readings_value_types(virtual_city):
    initialize_sensors()

    readings = generate_all_readings()

    for reading in readings:
        if reading["parameter"] == "Equipment Status":
            assert reading["value"] in EQUIPMENT_STATUS_VALUES
        else:
            assert isinstance(reading["value"], (int, float)), (
                f"Numeric parameter {reading['parameter']} produced "
                f"non-numeric value: {reading['value']!r}"
            )


def test_readings_sensor_ids_belong_to_assets(virtual_city):
    """Each reading's sensor_id must belong to the reported asset_id."""
    initialize_sensors()

    readings = generate_all_readings()

    for reading in readings:
        assert reading["sensor_id"].startswith(reading["asset_id"] + "-")
        assert reading["asset_id"] in ASSETS