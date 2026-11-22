from types import SimpleNamespace

import pytest

from backend.app.services.analytics_service import _detect_asset_anomalies


def make_entry(parameter, value, reading_id):
    if parameter == "Equipment Status":
        numeric_value = None
        text_value = str(value)
    else:
        numeric_value = float(value)
        text_value = None

    return {
        "parameter": parameter,
        "reading": SimpleNamespace(reading_id=reading_id),
        "numeric_value": numeric_value,
        "text_value": text_value,
    }


def detect(asset_type, *entries):
    asset = SimpleNamespace(asset_type=asset_type)
    return _detect_asset_anomalies(asset, list(entries))


def anomaly_types(results):
    return [item["anomaly_type"] for item in results]


@pytest.mark.parametrize(
    "asset_type, pressure, expected",
    [
        ("Pipeline", 39.99, ["Low Pressure"]),
        ("Pipeline", 40, []),
        ("Pipeline", 60, []),
        ("Pipeline", 60.01, ["High Pressure"]),
        ("Valve", 39.99, ["Low Pressure"]),
        ("Valve", 60.01, ["High Pressure"]),
        ("PumpStation", 59.99, ["Low Pressure"]),
        ("PumpStation", 60, []),
        ("PumpStation", 80, []),
        ("PumpStation", 80.01, ["High Pressure"]),
        ("Reservoir", 39, []),
        ("TreatmentFacility", 81, []),
    ],
)
def test_pressure_thresholds(asset_type, pressure, expected):
    results = detect(
        asset_type,
        make_entry("Pressure", pressure, 101),
    )

    assert anomaly_types(results) == expected


@pytest.mark.parametrize(
    "flow, expected",
    [
        (79.99, ["Low Flow"]),
        (80, []),
        (120, []),
    ],
)
def test_flow_threshold(flow, expected):
    results = detect(
        "Pipeline",
        make_entry("Flow Rate", flow, 201),
    )

    assert anomaly_types(results) == expected


@pytest.mark.parametrize(
    "flow, pressure, expected",
    [
        (79, 39.9, ["Low Pressure", "Low Flow", "Possible Leak"]),
        (79, 40, ["Low Flow"]),
        (80, 39.9, ["Low Pressure"]),
        (80, 40, []),
    ],
)
def test_possible_leak_requires_low_flow_and_low_pressure(
    flow, pressure, expected
):
    results = detect(
        "Pipeline",
        make_entry("Flow Rate", flow, 301),
        make_entry("Pressure", pressure, 302),
    )

    assert sorted(anomaly_types(results)) == sorted(expected)


def test_possible_leak_links_to_flow_reading():
    results = detect(
        "Pipeline",
        make_entry("Flow Rate", 70, 401),
        make_entry("Pressure", 35, 402),
    )

    leak = next(
        item for item in results
        if item["anomaly_type"] == "Possible Leak"
    )

    assert leak["sensor_reading_id"] == 401
    assert "Pressure reading ID: 402" in leak["description"]


@pytest.mark.parametrize(
    "parameter, value, asset_type, expected",
    [
        ("Temperature", 40.01, "PumpStation", ["Overheating"]),
        ("Temperature", 40, "PumpStation", []),
        ("Vibration", 5.01, "PumpStation", ["Excessive Vibration"]),
        ("Vibration", 5, "PumpStation", []),
        ("Power Consumption", 50.01, "PumpStation", ["Overpower"]),
        ("Power Consumption", 50, "PumpStation", []),
        ("Valve Position", 19.99, "Valve", ["Abnormal Valve Position"]),
        ("Valve Position", 20, "Valve", []),
        ("Valve Position", 80, "Valve", []),
        ("Valve Position", 80.01, "Valve", ["Abnormal Valve Position"]),
    ],
)
def test_equipment_numeric_thresholds(
    parameter, value, asset_type, expected
):
    results = detect(
        asset_type,
        make_entry(parameter, value, 501),
    )

    assert anomaly_types(results) == expected


def test_equipment_off_alone_is_not_a_failure():
    results = detect(
        "PumpStation",
        make_entry("Equipment Status", "OFF", 601),
    )

    assert anomaly_types(results) == []


def test_equipment_off_with_normal_pressure_is_not_a_failure():
    results = detect(
        "PumpStation",
        make_entry("Equipment Status", "OFF", 602),
        make_entry("Pressure", 60, 603),
    )

    assert anomaly_types(results) == []


def test_equipment_off_with_abnormal_pressure_detects_failure():
    results = detect(
        "PumpStation",
        make_entry("Pressure", 59, 604),
        make_entry("Equipment Status", "OFF", 605),
    )

    assert anomaly_types(results) == [
        "Low Pressure",
        "Possible Equipment Failure",
    ]

    failure = next(
        item for item in results
        if item["anomaly_type"] == "Possible Equipment Failure"
    )

    assert failure["sensor_reading_id"] == 605


def test_equipment_on_with_abnormal_pressure_does_not_detect_failure():
    results = detect(
        "PumpStation",
        make_entry("Pressure", 59, 606),
        make_entry("Equipment Status", "ON", 607),
    )

    assert anomaly_types(results) == ["Low Pressure"]


@pytest.mark.parametrize(
    "ph, expected",
    [
        (6.49, ["Abnormal pH"]),
        (6.5, []),
        (8.5, []),
        (8.51, ["Abnormal pH"]),
    ],
)
def test_ph_thresholds(ph, expected):
    results = detect(
        "TreatmentFacility",
        make_entry("pH", ph, 701),
    )

    assert anomaly_types(results) == expected


@pytest.mark.parametrize(
    "turbidity, expected",
    [
        (5, []),
        (5.01, ["High Turbidity"]),
    ],
)
def test_turbidity_threshold(turbidity, expected):
    results = detect(
        "TreatmentFacility",
        make_entry("Turbidity", turbidity, 801),
    )

    assert anomaly_types(results) == expected


@pytest.mark.parametrize(
    "temperature, expected",
    [
        (9.99, ["Abnormal Water Temperature"]),
        (10, []),
        (25, []),
        (25.01, ["Abnormal Water Temperature"]),
    ],
)
def test_water_temperature_thresholds(temperature, expected):
    results = detect(
        "TreatmentFacility",
        make_entry("Water Temperature", temperature, 901),
    )

    assert anomaly_types(results) == expected


@pytest.mark.parametrize(
    "level, expected",
    [
        (4.99, ["Abnormal Reservoir Level"]),
        (5, []),
        (15, []),
        (15.01, ["Abnormal Reservoir Level"]),
    ],
)
def test_water_level_thresholds(level, expected):
    results = detect(
        "Reservoir",
        make_entry("Water Level", level, 1001),
    )

    assert anomaly_types(results) == expected
