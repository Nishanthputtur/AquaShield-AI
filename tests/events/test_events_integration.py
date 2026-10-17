"""
Integration test for the complete AquaShield AI event layer.

Covers the pipeline:

    Virtual City
        -> 108 assets
        -> 328 virtual sensors
        -> 328 normal readings
        -> EventManager
        -> active event effects
        -> modified abnormal readings

The tests use the real city, sensor, and event modules. No mocks are
used for the core integration flow. Random numeric baselines are never
asserted directly; deterministic relationships within a single reading
list are used instead.

Run from the project root:

    python -m pytest tests/events/test_events_integration.py -v
"""

import pytest

from simulator.city.assets import ASSETS, AssetType
from simulator.city.virtual_city import create_virtual_city
from simulator.sensors import initialize_sensors, generate_all_readings

from simulator.events import (
    EventManager,
    LeakEvent,
    Leaks,
    DeteriorationEvent,
    PressureDropEvent,
    PumpFailureEvent,
    ValveFailureEvent,
    WaterQualityEvent,
)


# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------

EXPECTED_ASSETS = 108
EXPECTED_READINGS = 328

READING_KEYS = {
    "sensor_id",
    "asset_id",
    "parameter",
    "value",
    "unit",
    "timestamp",
}

PUBLIC_EVENT_NAMES = [
    "EventManager",
    "LeakEvent",
    "Leaks",
    "DeteriorationEvent",
    "PressureDropEvent",
    "PumpFailureEvent",
    "ValveFailureEvent",
    "WaterQualityEvent",
]


# ----------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------

@pytest.fixture(scope="module")
def virtual_city():
    """Create the virtual city once and initialize sensors."""
    city = create_virtual_city()
    initialize_sensors()
    return city


@pytest.fixture
def manager():
    """A fresh EventManager for each test, bound to the global ASSETS."""
    return EventManager(assets_by_id=ASSETS)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _find_first(asset_type, exclude_ids=None):
    """Return the first asset of the given type, skipping excluded IDs."""
    exclude_ids = exclude_ids or set()
    for asset in ASSETS.values():
        if asset.asset_type == asset_type and asset.id not in exclude_ids:
            return asset
    raise AssertionError(f"No asset of type {asset_type} found.")


def _find_n_of_type(asset_type, n):
    """Return the first n assets of the given type."""
    result = []
    for asset in ASSETS.values():
        if asset.asset_type == asset_type:
            result.append(asset)
            if len(result) >= n:
                return result
    raise AssertionError(f"Not enough {asset_type} assets (need {n}).")


def _find_reading(readings, asset_id, parameter):
    """Return the reading dict for (asset_id, parameter), or None."""
    for r in readings:
        if r["asset_id"] == asset_id and r["parameter"] == parameter:
            return r
    return None


def _readings_for_asset(readings, asset_id):
    """Return all readings belonging to one asset."""
    return [r for r in readings if r["asset_id"] == asset_id]


def _snapshot_asset_values(readings, asset_id):
    """Return {parameter: value} for one asset."""
    return {
        r["parameter"]: r["value"]
        for r in readings
        if r["asset_id"] == asset_id
    }


# ----------------------------------------------------------------------
# 1. Event package imports and import safety
# ----------------------------------------------------------------------

def test_event_package_imports_all_public_classes():
    import simulator.events as events_pkg

    for name in PUBLIC_EVENT_NAMES:
        assert hasattr(events_pkg, name), f"Missing public name: {name}"


def test_event_package_has_expected_dunder_all():
    import simulator.events as events_pkg

    for name in PUBLIC_EVENT_NAMES:
        assert name in events_pkg.__all__


def test_event_package_import_is_side_effect_free():
    """
    Importing simulator.events must not create module-level event
    instances, EventManager instances, readings, or threads.
    """
    import simulator.events as events_pkg

    for name in PUBLIC_EVENT_NAMES:
        obj = getattr(events_pkg, name)
        assert isinstance(obj, type), (
            f"{name} should be a class, not an instance: {obj!r}"
        )


# ----------------------------------------------------------------------
# 2. Baseline: city + sensors + readings
# ----------------------------------------------------------------------

def test_baseline_city_and_reading_count(virtual_city):
    assert len(virtual_city.cities) == 4
    assert len(virtual_city.zones) == 16
    assert len(virtual_city.assets) == EXPECTED_ASSETS

    readings = generate_all_readings()
    assert isinstance(readings, list)
    assert len(readings) == EXPECTED_READINGS


def test_baseline_reading_schema(virtual_city):
    readings = generate_all_readings()
    for r in readings:
        assert set(r.keys()) == READING_KEYS


# ----------------------------------------------------------------------
# 3. Reading schema preserved by event processing
# ----------------------------------------------------------------------

def test_reading_schema_preserved_after_event_processing(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    leak = LeakEvent(event_id="schema-1", asset_id=pipeline.id, severity=0.5)
    manager.register_event(leak)
    manager.activate_event("schema-1")

    readings = generate_all_readings()
    modified = manager.apply_events(readings)

    assert len(modified) == EXPECTED_READINGS
    for r in modified:
        assert set(r.keys()) == READING_KEYS


# ----------------------------------------------------------------------
# 4. LeakEvent
# ----------------------------------------------------------------------

def test_leak_modifies_target_pipeline(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    leak = LeakEvent(event_id="leak-1", asset_id=pipeline.id, severity=0.5)
    manager.register_event(leak)
    manager.activate_event("leak-1")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    b_flow = _find_reading(baseline, pipeline.id, "Flow Rate")
    m_flow = _find_reading(modified, pipeline.id, "Flow Rate")
    assert b_flow is not None and m_flow is not None
    assert m_flow["value"] < b_flow["value"]

    b_pressure = _find_reading(baseline, pipeline.id, "Pressure")
    m_pressure = _find_reading(modified, pipeline.id, "Pressure")
    assert b_pressure is not None and m_pressure is not None
    assert m_pressure["value"] < b_pressure["value"]

    # Deterministic relationship (from LeakEvent class constants).
    expected_flow = round(
        b_flow["value"] * (1.0 - 0.5 * LeakEvent.MAX_FLOW_REDUCTION), 2
    )
    expected_pressure = round(
        b_pressure["value"] * (1.0 - 0.5 * LeakEvent.MAX_PRESSURE_REDUCTION), 2
    )
    assert m_flow["value"] == expected_flow
    assert m_pressure["value"] == expected_pressure


def test_leak_does_not_affect_unrelated_assets(virtual_city, manager):
    pipeline_a, pipeline_b = _find_n_of_type(AssetType.PIPELINE, 2)

    leak = LeakEvent(event_id="leak-local", asset_id=pipeline_a.id, severity=0.7)
    manager.register_event(leak)
    manager.activate_event("leak-local")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    b_other = _snapshot_asset_values(baseline, pipeline_b.id)
    m_other = _snapshot_asset_values(modified, pipeline_b.id)
    assert b_other == m_other


def test_inactive_leak_does_not_modify(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    leak = LeakEvent(event_id="leak-inactive", asset_id=pipeline.id, severity=0.9)
    manager.register_event(leak)
    # Note: never activated.

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    b = _snapshot_asset_values(baseline, pipeline.id)
    m = _snapshot_asset_values(modified, pipeline.id)
    assert b == m


# ----------------------------------------------------------------------
# 5. Multiple leaks
# ----------------------------------------------------------------------

def test_leaks_collection_tracks_multiple_and_isolates(virtual_city):
    pipeline_a, pipeline_b = _find_n_of_type(AssetType.PIPELINE, 2)

    leaks = Leaks()
    leaks.add(LeakEvent(event_id="L-a", asset_id=pipeline_a.id, severity=0.6))
    leaks.add(LeakEvent(event_id="L-b", asset_id=pipeline_b.id, severity=0.6))
    leaks.activate_all()

    assert leaks.count() == 2
    assert leaks.active_count() == 2

    baseline = generate_all_readings()
    modified = leaks.apply_active(baseline, ASSETS)

    a_mod = _find_reading(modified, pipeline_a.id, "Flow Rate")
    b_mod = _find_reading(modified, pipeline_b.id, "Flow Rate")
    a_base = _find_reading(baseline, pipeline_a.id, "Flow Rate")
    b_base = _find_reading(baseline, pipeline_b.id, "Flow Rate")

    assert a_mod["value"] < a_base["value"]
    assert b_mod["value"] < b_base["value"]


def test_leaks_deactivate_one_keeps_other_active(virtual_city):
    pipeline_a, pipeline_b = _find_n_of_type(AssetType.PIPELINE, 2)

    leaks = Leaks()
    leaks.add(LeakEvent(event_id="L-a", asset_id=pipeline_a.id, severity=0.6))
    leaks.add(LeakEvent(event_id="L-b", asset_id=pipeline_b.id, severity=0.6))
    leaks.activate_all()

    leaks.deactivate("L-a")

    assert leaks.get("L-a").active is False
    assert leaks.get("L-b").active is True
    assert leaks.active_count() == 1


def test_leaks_duplicate_event_id_rejected(virtual_city):
    pipeline = _find_first(AssetType.PIPELINE)

    leaks = Leaks()
    leaks.add(LeakEvent(event_id="dup", asset_id=pipeline.id, severity=0.3))

    with pytest.raises(ValueError):
        leaks.add(LeakEvent(event_id="dup", asset_id=pipeline.id, severity=0.3))


# ----------------------------------------------------------------------
# 6. PressureDropEvent
# ----------------------------------------------------------------------

def test_pressure_drop_modifies_target(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    event = PressureDropEvent(
        event_id="pd-1", asset_id=pipeline.id, severity=0.6
    )
    manager.register_event(event)
    manager.activate_event("pd-1")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    b = _find_reading(baseline, pipeline.id, "Pressure")
    m = _find_reading(modified, pipeline.id, "Pressure")
    assert m["value"] < b["value"]

    # Deterministic per PressureDropEvent constants.
    expected = round(
        b["value"] * (1.0 - 0.6 * PressureDropEvent.MAX_PRESSURE_REDUCTION), 2
    )
    assert m["value"] == expected


# ----------------------------------------------------------------------
# 7. PumpFailureEvent
# ----------------------------------------------------------------------

def test_pump_failure_modifies_pump_station(virtual_city, manager):
    pump = _find_first(AssetType.PUMP_STATION)

    event = PumpFailureEvent(event_id="pf-1", asset_id=pump.id, severity=0.9)
    manager.register_event(event)
    manager.activate_event("pf-1")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    # Pressure and flow decrease.
    assert _find_reading(modified, pump.id, "Pressure")["value"] < \
           _find_reading(baseline, pump.id, "Pressure")["value"]
    assert _find_reading(modified, pump.id, "Flow Rate")["value"] < \
           _find_reading(baseline, pump.id, "Flow Rate")["value"]

    # Temperature, vibration, power increase.
    assert _find_reading(modified, pump.id, "Temperature")["value"] > \
           _find_reading(baseline, pump.id, "Temperature")["value"]
    assert _find_reading(modified, pump.id, "Vibration")["value"] > \
           _find_reading(baseline, pump.id, "Vibration")["value"]
    assert _find_reading(modified, pump.id, "Power Consumption")["value"] > \
           _find_reading(baseline, pump.id, "Power Consumption")["value"]

    # Equipment Status becomes "OFF" above the failure threshold.
    status = _find_reading(modified, pump.id, "Equipment Status")
    assert status["value"] == "OFF"


def test_pump_failure_rejects_non_pump_target(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    event = PumpFailureEvent(event_id="pf-bad", asset_id=pipeline.id, severity=0.5)

    with pytest.raises(ValueError):
        manager.register_event(event)


# ----------------------------------------------------------------------
# 8. ValveFailureEvent
# ----------------------------------------------------------------------

def test_valve_failure_modifies_valve(virtual_city, manager):
    valve = _find_first(AssetType.VALVE)

    event = ValveFailureEvent(event_id="vf-1", asset_id=valve.id, severity=0.8)
    manager.register_event(event)
    manager.activate_event("vf-1")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    # Valve Position decreases.
    assert _find_reading(modified, valve.id, "Valve Position")["value"] < \
           _find_reading(baseline, valve.id, "Valve Position")["value"]

    # Flow Rate decreases.
    assert _find_reading(modified, valve.id, "Flow Rate")["value"] < \
           _find_reading(baseline, valve.id, "Flow Rate")["value"]

    # Pressure increases (back pressure at restricted valve).
    assert _find_reading(modified, valve.id, "Pressure")["value"] > \
           _find_reading(baseline, valve.id, "Pressure")["value"]


def test_valve_failure_rejects_non_valve_target(virtual_city, manager):
    pump = _find_first(AssetType.PUMP_STATION)

    event = ValveFailureEvent(event_id="vf-bad", asset_id=pump.id, severity=0.5)

    with pytest.raises(ValueError):
        manager.register_event(event)


# ----------------------------------------------------------------------
# 9. WaterQualityEvent
# ----------------------------------------------------------------------

def test_water_quality_on_reservoir(virtual_city, manager):
    reservoir = _find_first(AssetType.RESERVOIR)

    event = WaterQualityEvent(event_id="wq-r", asset_id=reservoir.id, severity=0.7)
    manager.register_event(event)
    manager.activate_event("wq-r")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    # pH decreases.
    assert _find_reading(modified, reservoir.id, "pH")["value"] < \
           _find_reading(baseline, reservoir.id, "pH")["value"]

    # Turbidity increases.
    assert _find_reading(modified, reservoir.id, "Turbidity")["value"] > \
           _find_reading(baseline, reservoir.id, "Turbidity")["value"]

    # Water Temperature increases.
    assert _find_reading(modified, reservoir.id, "Water Temperature")["value"] > \
           _find_reading(baseline, reservoir.id, "Water Temperature")["value"]

    # Water Level is NOT affected.
    assert _find_reading(modified, reservoir.id, "Water Level")["value"] == \
           _find_reading(baseline, reservoir.id, "Water Level")["value"]


def test_water_quality_on_treatment_facility(virtual_city, manager):
    tf = _find_first(AssetType.TREATMENT_FACILITY)

    event = WaterQualityEvent(event_id="wq-tf", asset_id=tf.id, severity=0.7)
    manager.register_event(event)
    manager.activate_event("wq-tf")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    assert _find_reading(modified, tf.id, "pH")["value"] < \
           _find_reading(baseline, tf.id, "pH")["value"]
    assert _find_reading(modified, tf.id, "Turbidity")["value"] > \
           _find_reading(baseline, tf.id, "Turbidity")["value"]
    assert _find_reading(modified, tf.id, "Water Temperature")["value"] > \
           _find_reading(baseline, tf.id, "Water Temperature")["value"]


def test_water_quality_rejects_unsupported_asset(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    event = WaterQualityEvent(event_id="wq-bad", asset_id=pipeline.id, severity=0.5)

    with pytest.raises(ValueError):
        manager.register_event(event)


def test_water_quality_pH_stays_in_valid_range(virtual_city, manager):
    reservoir = _find_first(AssetType.RESERVOIR)

    event = WaterQualityEvent(event_id="wq-range", asset_id=reservoir.id, severity=1.0)
    manager.register_event(event)
    manager.activate_event("wq-range")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    ph = _find_reading(modified, reservoir.id, "pH")["value"]
    assert 0.0 <= ph <= 14.0


# ----------------------------------------------------------------------
# 10. DeteriorationEvent
# ----------------------------------------------------------------------

def test_deterioration_advances_and_resets(virtual_city):
    pipeline = _find_first(AssetType.PIPELINE)

    event = DeteriorationEvent(event_id="det-1", asset_id=pipeline.id)
    assert event.deterioration_level == 0.0

    event.advance()
    assert event.deterioration_level == pytest.approx(0.05)

    event.advance(0.20)
    assert event.deterioration_level == pytest.approx(0.25)

    event.set_level(0.5)
    assert event.deterioration_level == 0.5

    event.reset()
    assert event.deterioration_level == 0.0
    assert event.active is False


def test_deterioration_modifies_target_readings(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    event = DeteriorationEvent(
        event_id="det-active",
        asset_id=pipeline.id,
        initial_level=0.7,
    )
    manager.register_event(event)
    manager.activate_event("det-active")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    assert _find_reading(modified, pipeline.id, "Pressure")["value"] < \
           _find_reading(baseline, pipeline.id, "Pressure")["value"]
    assert _find_reading(modified, pipeline.id, "Flow Rate")["value"] < \
           _find_reading(baseline, pipeline.id, "Flow Rate")["value"]


# ----------------------------------------------------------------------
# 11. EventManager coordination
# ----------------------------------------------------------------------

def test_event_manager_coordinates_multiple_events(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)
    pump = _find_first(AssetType.PUMP_STATION)

    leak = LeakEvent(event_id="coord-leak", asset_id=pipeline.id, severity=0.5)
    pf = PumpFailureEvent(event_id="coord-pf", asset_id=pump.id, severity=0.8)

    manager.register_event(leak)
    manager.register_event(pf)
    manager.activate_event("coord-leak")
    manager.activate_event("coord-pf")

    assert len(manager.get_active_events()) == 2

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    # Both targets affected.
    assert _find_reading(modified, pipeline.id, "Pressure")["value"] < \
           _find_reading(baseline, pipeline.id, "Pressure")["value"]
    assert _find_reading(modified, pump.id, "Pressure")["value"] < \
           _find_reading(baseline, pump.id, "Pressure")["value"]

    # Unrelated assets untouched.
    other_pump = _find_first(
        AssetType.PUMP_STATION, exclude_ids={pump.id}
    )
    assert _snapshot_asset_values(baseline, other_pump.id) == \
           _snapshot_asset_values(modified, other_pump.id)


# ----------------------------------------------------------------------
# 12. Event lifecycle
# ----------------------------------------------------------------------

def test_event_lifecycle(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    leak = LeakEvent(event_id="lc-1", asset_id=pipeline.id, severity=0.5)
    manager.register_event(leak)

    assert manager.has_event("lc-1")
    assert manager.is_active("lc-1") is False

    manager.activate_event("lc-1")
    assert manager.is_active("lc-1") is True

    manager.deactivate_event("lc-1")
    assert manager.is_active("lc-1") is False

    manager.remove_event("lc-1")
    assert manager.has_event("lc-1") is False


def test_reset_events_clears_state(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    leak = LeakEvent(event_id="reset-1", asset_id=pipeline.id, severity=0.5)
    manager.register_event(leak)
    manager.activate_event("reset-1")

    assert len(manager.get_active_events()) == 1

    manager.reset_events()

    assert len(manager.get_active_events()) == 0
    assert manager.has_event("reset-1") is False


# ----------------------------------------------------------------------
# 13. Reading count preservation
# ----------------------------------------------------------------------

def test_reading_count_preserved_across_events(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)
    pump = _find_first(AssetType.PUMP_STATION)

    manager.register_event(
        LeakEvent(event_id="cnt-leak", asset_id=pipeline.id, severity=0.5)
    )
    manager.register_event(
        PumpFailureEvent(event_id="cnt-pf", asset_id=pump.id, severity=0.7)
    )
    manager.activate_event("cnt-leak")
    manager.activate_event("cnt-pf")

    baseline = generate_all_readings()
    modified = manager.apply_events(baseline)

    assert len(baseline) == EXPECTED_READINGS
    assert len(modified) == EXPECTED_READINGS


# ----------------------------------------------------------------------
# 14. Sensor object preservation
# ----------------------------------------------------------------------

def test_sensor_objects_not_replaced_by_event_processing(virtual_city, manager):
    before = {
        asset.id: [id(s) for s in asset.sensors]
        for asset in virtual_city.assets
    }

    pipeline = _find_first(AssetType.PIPELINE)
    manager.register_event(
        LeakEvent(event_id="sensor-safe", asset_id=pipeline.id, severity=0.6)
    )
    manager.activate_event("sensor-safe")

    readings = generate_all_readings()
    manager.apply_events(readings)

    after = {
        asset.id: [id(s) for s in asset.sensors]
        for asset in virtual_city.assets
    }

    assert before == after


# ----------------------------------------------------------------------
# 15. Sequential activation / deactivation
# ----------------------------------------------------------------------

def test_sequential_active_then_inactive_readings(virtual_city, manager):
    pipeline = _find_first(AssetType.PIPELINE)

    manager.register_event(
        LeakEvent(event_id="seq-1", asset_id=pipeline.id, severity=0.6)
    )

    # Active phase
    manager.activate_event("seq-1")
    baseline_active = generate_all_readings()
    modified_active = manager.apply_events(baseline_active)

    assert _find_reading(modified_active, pipeline.id, "Pressure")["value"] < \
           _find_reading(baseline_active, pipeline.id, "Pressure")["value"]

    # Stop phase
    manager.deactivate_event("seq-1")
    baseline_stopped = generate_all_readings()
    modified_stopped = manager.apply_events(baseline_stopped)

    assert _snapshot_asset_values(baseline_stopped, pipeline.id) == \
           _snapshot_asset_values(modified_stopped, pipeline.id)


# ----------------------------------------------------------------------
# 16. Invalid target handling
# ----------------------------------------------------------------------

def test_leak_rejects_non_pipeline_target(virtual_city, manager):
    reservoir = _find_first(AssetType.RESERVOIR)
    event = LeakEvent(event_id="bad-leak", asset_id=reservoir.id, severity=0.5)

    with pytest.raises(ValueError):
        manager.register_event(event)


def test_pressure_drop_rejects_unsupported_target(virtual_city, manager):
    reservoir = _find_first(AssetType.RESERVOIR)
    event = PressureDropEvent(event_id="bad-pd", asset_id=reservoir.id, severity=0.5)

    with pytest.raises(ValueError):
        manager.register_event(event)


# ----------------------------------------------------------------------
# 17. Severity validation
# ----------------------------------------------------------------------

def test_invalid_severity_rejected(virtual_city):
    pipeline = _find_first(AssetType.PIPELINE)

    with pytest.raises(ValueError):
        LeakEvent(event_id="s1", asset_id=pipeline.id, severity=-0.1)

    with pytest.raises(ValueError):
        LeakEvent(event_id="s2", asset_id=pipeline.id, severity=1.5)

    with pytest.raises(ValueError):
        PumpFailureEvent(event_id="s3", asset_id=pipeline.id, severity=2.0)


def test_invalid_event_id_rejected():
    with pytest.raises(ValueError):
        LeakEvent(event_id="", asset_id="C1-P-001", severity=0.5)

    with pytest.raises(ValueError):
        LeakEvent(event_id="   ", asset_id="C1-P-001", severity=0.5)


def test_invalid_asset_id_rejected():
    with pytest.raises(ValueError):
        LeakEvent(event_id="ok", asset_id="", severity=0.5)

    with pytest.raises(ValueError):
        LeakEvent(event_id="ok", asset_id="   ", severity=0.5)