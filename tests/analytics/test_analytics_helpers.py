from types import SimpleNamespace

import pytest

from backend.app.services.analytics_service import (
    _get_sensor_parameter,
    _parse_reading,
)


@pytest.mark.parametrize(
    "sensor_type, sensor_name, expected",
    [
        ("Flow", "C1-PIPE-001-FLOW", "Flow Rate"),
        ("Pressure", "C1-PIPE-001-PRESSURE", "Pressure"),
        ("Level", "C1-RES-001-LEVEL", "Water Level"),
        ("Water Temperature", "C1-TF-001-WATER-TEMPERATURE", "Water Temperature"),
        ("pH", "C1-TF-001-PH", "pH"),
        ("Turbidity", "C1-TF-001-TURBIDITY", "Turbidity"),
        ("Equipment Condition", "C1-PS-001-EQUIPMENT-STATUS", "Equipment Status"),
        ("Equipment Condition", "C1-PS-001-VIBRATION", "Vibration"),
        ("Equipment Condition", "C1-PS-001-POWER", "Power Consumption"),
        ("Equipment Condition", "C1-PS-001-TEMPERATURE", "Temperature"),
        ("Equipment Condition", "C1-V-001-POSITION", "Valve Position"),
    ],
)
def test_get_sensor_parameter(sensor_type, sensor_name, expected):
    sensor = SimpleNamespace(
        sensor_type=sensor_type,
        sensor_name=sensor_name,
    )

    assert _get_sensor_parameter(sensor) == expected


def test_unknown_sensor_type_returns_none():
    sensor = SimpleNamespace(
        sensor_type="Unknown",
        sensor_name="UNKNOWN-001",
    )

    assert _get_sensor_parameter(sensor) is None


def test_unknown_equipment_sensor_name_returns_none():
    sensor = SimpleNamespace(
        sensor_type="Equipment Condition",
        sensor_name="C1-PS-001-UNKNOWN",
    )

    assert _get_sensor_parameter(sensor) is None


def test_parse_numeric_column():
    reading = SimpleNamespace(
        reading_value_numeric=42.5,
        reading_value_text=None,
    )

    assert _parse_reading(reading) == (42.5, None)


def test_parse_numeric_text():
    reading = SimpleNamespace(
        reading_value_numeric=None,
        reading_value_text="31.29",
    )

    assert _parse_reading(reading) == (31.29, None)


def test_parse_equipment_status_text():
    reading = SimpleNamespace(
        reading_value_numeric=None,
        reading_value_text="ON",
    )

    assert _parse_reading(reading) == (None, "ON")


def test_parse_text_strips_whitespace_and_uppercases():
    reading = SimpleNamespace(
        reading_value_numeric=None,
        reading_value_text=" off ",
    )

    assert _parse_reading(reading) == (None, "OFF")


def test_parse_empty_reading():
    reading = SimpleNamespace(
        reading_value_numeric=None,
        reading_value_text=None,
    )

    assert _parse_reading(reading) == (None, None)
