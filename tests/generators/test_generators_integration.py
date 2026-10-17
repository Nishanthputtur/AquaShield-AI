"""
Integration tests for the AquaShield AI generator layer.

Covers:
    - Package import boundary and side-effect-free import
    - Simulation lifecycle: valid transitions
    - Simulation lifecycle: invalid transitions raise RuntimeError
    - Tick behaviour: advances on success, preserved on stop, reset clears,
      unchanged after an unexpected exception during generation
    - Reading generation: 328 readings, six-field schema, RUNNING only
    - Event registration: all six event types, validations, no partial state
    - Event activation / deactivation / listing
    - Reset clears registered events (from every state)
    - Active events modify only their target (frozen-baseline tests)
    - Full backend-facing workflow through the package

The existing sensor and event integration tests are unchanged. This
file tests the generator layer that coordinates them.
"""

import pytest

from simulator.city.assets import ASSETS
from simulator.city.virtual_city import create_virtual_city
from simulator.generators import SimulationGenerator, SimulationState


READING_KEYS = {
    "sensor_id",
    "asset_id",
    "parameter",
    "value",
    "unit",
    "timestamp",
}

EXPECTED_READINGS = 328


# ----------------------------------------------------------------------
# Fixtures: fresh virtual city per test.
#
# create_virtual_city() clears and repopulates ASSETS and returns new
# Asset objects with empty sensor lists. Each test that mutates state
# gets a clean world.
# ----------------------------------------------------------------------

@pytest.fixture
def fresh_city():
    return create_virtual_city()


@pytest.fixture
def generator(fresh_city):
    return SimulationGenerator()


@pytest.fixture
def running_generator(fresh_city):
    gen = SimulationGenerator()
    gen.start()
    return gen


# ----------------------------------------------------------------------
# Package boundary
# ----------------------------------------------------------------------

def test_package_public_api():
    import simulator.generators as pkg
    assert pkg.__all__ == ["SimulationGenerator", "SimulationState"]
    assert pkg.SimulationGenerator is SimulationGenerator
    assert pkg.SimulationState is SimulationState


def test_package_import_is_side_effect_free():
    """Importing simulator.generators in a fresh Python process must
    not populate ASSETS or perform any other observable side effect.

    A subprocess is required because the parent test process already
    imports the package at module load, so an in-process import would
    read from Python's module cache instead of testing fresh behaviour.
    """
    import subprocess
    import sys
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[2]

    code = (
        "import sys\n"
        "from simulator.city.assets import ASSETS\n"
        "before = len(ASSETS)\n"
        "assert 'simulator.generators' not in sys.modules, "
        "'simulator.generators already in sys.modules'\n"
        "import simulator.generators\n"
        "after = len(ASSETS)\n"
        "assert before == after, "
        "f'ASSETS populated during import: {before} -> {after}'\n"
        "assert 'simulator.generators' in sys.modules\n"
        "print('OK')\n"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    assert result.returncode == 0, (
        f"subprocess failed\n"
        f"stdout: {result.stdout}\n"
        f"stderr: {result.stderr}"
    )
    assert "OK" in result.stdout


# ----------------------------------------------------------------------
# Lifecycle: valid transitions
# ----------------------------------------------------------------------

def test_initial_state_is_idle(generator):
    assert generator.state == SimulationState.IDLE
    assert generator.tick == 0


def test_start_transitions_to_running(generator):
    generator.start()
    assert generator.state == SimulationState.RUNNING
    assert generator.tick == 0


def test_pause_transitions_to_paused(running_generator):
    running_generator.pause()
    assert running_generator.state == SimulationState.PAUSED


def test_resume_transitions_to_running(running_generator):
    running_generator.pause()
    running_generator.resume()
    assert running_generator.state == SimulationState.RUNNING


def test_stop_transitions_to_stopped(running_generator):
    running_generator.stop()
    assert running_generator.state == SimulationState.STOPPED


def test_reset_from_running_returns_to_idle(running_generator):
    running_generator.reset()
    assert running_generator.state == SimulationState.IDLE
    assert running_generator.tick == 0


def test_reset_from_stopped_returns_to_idle(running_generator):
    running_generator.stop()
    running_generator.reset()
    assert running_generator.state == SimulationState.IDLE
    assert running_generator.tick == 0


def test_reset_from_paused_returns_to_idle(running_generator):
    """Reset must be permitted from PAUSED, not only from RUNNING
    or STOPPED. The specification allows Reset from every state."""
    running_generator.generate()
    running_generator.pause()
    assert running_generator.state == SimulationState.PAUSED
    assert running_generator.tick == 1

    running_generator.reset()

    assert running_generator.state == SimulationState.IDLE
    assert running_generator.tick == 0
    assert running_generator.list_events() == []


def test_reset_from_paused_clears_active_events(running_generator):
    """Reset from PAUSED must also clear any active events, so a
    later start() begins from a clean slate."""
    running_generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    running_generator.activate_event("leak-1")
    running_generator.pause()

    running_generator.reset()

    assert running_generator.state == SimulationState.IDLE
    assert running_generator.list_events() == []

    # A fresh start() must not resurrect the previous event.
    running_generator.start()
    running_generator.register_event("leak", "leak-2", "C1-P-002", 0.5)
    events = running_generator.list_events()
    assert len(events) == 1
    assert events[0]["event_id"] == "leak-2"


# ----------------------------------------------------------------------
# Lifecycle: invalid transitions
# ----------------------------------------------------------------------

def test_pause_from_idle_raises(generator):
    with pytest.raises(RuntimeError):
        generator.pause()


def test_resume_from_idle_raises(generator):
    with pytest.raises(RuntimeError):
        generator.resume()


def test_stop_from_idle_raises(generator):
    with pytest.raises(RuntimeError):
        generator.stop()


def test_generate_from_idle_raises(generator):
    with pytest.raises(RuntimeError):
        generator.generate()


def test_start_from_running_raises(running_generator):
    with pytest.raises(RuntimeError):
        running_generator.start()


def test_resume_from_running_raises(running_generator):
    with pytest.raises(RuntimeError):
        running_generator.resume()


def test_pause_from_paused_raises(running_generator):
    running_generator.pause()
    with pytest.raises(RuntimeError):
        running_generator.pause()


def test_generate_from_paused_raises(running_generator):
    running_generator.pause()
    with pytest.raises(RuntimeError):
        running_generator.generate()


def test_start_from_stopped_raises(running_generator):
    running_generator.stop()
    with pytest.raises(RuntimeError):
        running_generator.start()


def test_generate_from_stopped_raises(running_generator):
    running_generator.stop()
    with pytest.raises(RuntimeError):
        running_generator.generate()


# ----------------------------------------------------------------------
# Tick behaviour
# ----------------------------------------------------------------------

def test_tick_advances_on_successful_generate(running_generator):
    assert running_generator.tick == 0
    running_generator.generate()
    assert running_generator.tick == 1
    running_generator.generate()
    assert running_generator.tick == 2


def test_failed_generate_does_not_advance_tick(running_generator):
    running_generator.generate()
    assert running_generator.tick == 1
    running_generator.pause()
    with pytest.raises(RuntimeError):
        running_generator.generate()
    assert running_generator.tick == 1


def test_generate_exception_while_running_does_not_advance_tick(
    running_generator, monkeypatch
):
    """If reading generation raises unexpectedly while RUNNING,
    the tick must not advance and state must remain RUNNING.

    Unlike the PAUSED test, this exercises the case where generate()
    is called in a valid state but an internal failure (sensor error,
    event error) interrupts the cycle. The tick must remain consistent
    with the number of *successful* cycles, not the number of attempts.
    """
    from simulator.generators import operational

    # One successful cycle first so we have a non-zero baseline.
    running_generator.generate()
    assert running_generator.tick == 1

    # Force the next generation to fail at the reading-generation step.
    def boom():
        raise RuntimeError("simulated sensor failure")

    monkeypatch.setattr(operational, "get_normal_readings", boom)

    with pytest.raises(RuntimeError, match="simulated sensor failure"):
        running_generator.generate()

    # State is unchanged: still RUNNING, tick not advanced.
    assert running_generator.state == SimulationState.RUNNING
    assert running_generator.tick == 1

    # Recover: undo the monkeypatch, generate must work again.
    monkeypatch.undo()
    readings = running_generator.generate()
    assert len(readings) == EXPECTED_READINGS
    assert running_generator.tick == 2


def test_stop_preserves_tick(running_generator):
    running_generator.generate()
    running_generator.generate()
    assert running_generator.tick == 2
    running_generator.stop()
    assert running_generator.tick == 2


def test_reset_clears_tick(running_generator):
    running_generator.generate()
    running_generator.generate()
    running_generator.reset()
    assert running_generator.tick == 0


def test_start_resets_tick_to_zero_after_reset(running_generator):
    running_generator.generate()
    running_generator.reset()
    running_generator.start()
    assert running_generator.tick == 0


# ----------------------------------------------------------------------
# Reading generation
# ----------------------------------------------------------------------

def test_generate_returns_328_readings(running_generator):
    readings = running_generator.generate()
    assert isinstance(readings, list)
    assert len(readings) == EXPECTED_READINGS


def test_generate_preserves_reading_schema(running_generator):
    readings = running_generator.generate()
    for reading in readings:
        assert set(reading.keys()) == READING_KEYS


def test_generate_multiple_cycles_all_have_328(running_generator):
    for _ in range(3):
        readings = running_generator.generate()
        assert len(readings) == EXPECTED_READINGS


def test_generate_does_not_replace_sensor_objects(running_generator):
    """generate() must not replace or reconstruct sensor objects.

    The same sensor instances must remain attached to each asset across
    multiple generate() calls. Guards against event processing or
    generator internals accidentally replacing sensors rather than
    modifying readings.
    """
    from simulator.city.assets import ASSETS

    # First generate to ensure sensors are attached.
    running_generator.generate()

    before = {
        asset_id: [id(s) for s in asset.sensors]
        for asset_id, asset in ASSETS.items()
    }
    assert len(before) == 108, "expected 108 assets"
    assert sum(len(ids) for ids in before.values()) == 328, (
        "expected 328 total sensors"
    )

    # Run several more generate cycles.
    running_generator.generate()
    running_generator.generate()
    running_generator.generate()

    after = {
        asset_id: [id(s) for s in asset.sensors]
        for asset_id, asset in ASSETS.items()
    }

    assert after == before, (
        "generate() must not replace sensor objects; "
        "the same instances must remain attached to each asset"
    )


# ----------------------------------------------------------------------
# Event registration
# ----------------------------------------------------------------------

def test_register_all_six_event_types(generator):
    cases = [
        ("leak",          "C1-P-001"),
        ("deterioration", "C1-P-002"),
        ("pressure_drop", "C1-P-003"),
        ("pump_failure",  "C1-PS-001"),
        ("valve_failure", "C1-V-001"),
        ("water_quality", "C1-R-001"),
    ]
    for i, (etype, aid) in enumerate(cases):
        generator.register_event(etype, f"ev-{i}", aid, 0.3)
    events = generator.list_events()
    assert len(events) == 6


def test_register_unknown_event_type_raises(generator):
    with pytest.raises(ValueError):
        generator.register_event("bogus", "ev-x", "C1-P-001", 0.5)
    assert generator.list_events() == []


def test_register_invalid_severity_negative_raises(generator):
    with pytest.raises(ValueError):
        generator.register_event("leak", "ev-x", "C1-P-001", -0.1)
    assert generator.list_events() == []


def test_register_invalid_severity_above_one_raises(generator):
    with pytest.raises(ValueError):
        generator.register_event("leak", "ev-x", "C1-P-001", 1.5)
    assert generator.list_events() == []


def test_register_severity_non_numeric_raises(generator):
    with pytest.raises(ValueError):
        generator.register_event("leak", "ev-x", "C1-P-001", "high")
    assert generator.list_events() == []


def test_register_wrong_asset_type_raises(generator):
    # pump_failure on a pipeline must be rejected by the event class.
    with pytest.raises(ValueError):
        generator.register_event("pump_failure", "ev-x", "C1-P-001", 0.5)
    assert generator.list_events() == []


def test_register_unknown_asset_id_raises(generator):
    with pytest.raises(ValueError):
        generator.register_event("leak", "ev-x", "XX-UNKNOWN", 0.5)
    assert generator.list_events() == []


def test_register_duplicate_event_id_raises(generator):
    generator.register_event("leak", "ev-1", "C1-P-001", 0.5)
    with pytest.raises(ValueError):
        generator.register_event("leak", "ev-1", "C1-P-002", 0.5)


# ----------------------------------------------------------------------
# Event activation and listing
# ----------------------------------------------------------------------

def test_list_events_empty_initially(generator):
    assert generator.list_events() == []


def test_activate_and_deactivate_event(generator):
    generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    generator.activate_event("leak-1")
    events = generator.list_events()
    assert len(events) == 1
    assert events[0]["active"] is True

    generator.deactivate_event("leak-1")
    events = generator.list_events()
    assert events[0]["active"] is False


def test_activate_unknown_event_raises(generator):
    with pytest.raises(KeyError):
        generator.activate_event("does-not-exist")


def test_deactivate_unknown_event_raises(generator):
    with pytest.raises(KeyError):
        generator.deactivate_event("does-not-exist")


# ----------------------------------------------------------------------
# Reset clears events
# ----------------------------------------------------------------------

def test_reset_clears_registered_events(generator):
    generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    generator.register_event("leak", "leak-2", "C1-P-002", 0.5)
    assert len(generator.list_events()) == 2
    generator.reset()
    assert generator.list_events() == []


def test_reset_clears_active_state(generator):
    generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    generator.activate_event("leak-1")
    generator.reset()
    generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    events = generator.list_events()
    assert events[0]["active"] is False


# ----------------------------------------------------------------------
# Active events affect readings (frozen baseline)
#
# Sensors are random on each read(), so comparing two independent
# generate() calls is meaningless: every reading differs from sensor
# randomness alone. These tests freeze get_normal_readings() inside
# the operational module so the only difference between calls is the
# active event.
# ----------------------------------------------------------------------

def test_active_leak_reduces_flow_and_pressure(running_generator, monkeypatch):
    """A leak at severity 0.5 must reduce Flow Rate and Pressure on the
    target pipeline, and only on the target pipeline."""
    import copy
    from simulator.generators import operational

    fixed_baseline = [
        {
            "sensor_id": "C1-P-001-FLOW",
            "asset_id": "C1-P-001",
            "parameter": "Flow Rate",
            "value": 100.0,
            "unit": "L/min",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "sensor_id": "C1-P-001-PRESSURE",
            "asset_id": "C1-P-001",
            "parameter": "Pressure",
            "value": 50.0,
            "unit": "PSI",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "sensor_id": "C1-P-002-FLOW",
            "asset_id": "C1-P-002",
            "parameter": "Flow Rate",
            "value": 100.0,
            "unit": "L/min",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "sensor_id": "C1-P-002-PRESSURE",
            "asset_id": "C1-P-002",
            "parameter": "Pressure",
            "value": 50.0,
            "unit": "PSI",
            "timestamp": "2024-01-01T00:00:00",
        },
    ]

    monkeypatch.setattr(
        operational,
        "get_normal_readings",
        lambda: copy.deepcopy(fixed_baseline),
    )

    baseline = running_generator.generate()
    running_generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    running_generator.activate_event("leak-1")
    modified = running_generator.generate()

    # Target: both Flow Rate and Pressure must decrease.
    target_flow = next(
        r for r in modified
        if r["asset_id"] == "C1-P-001" and r["parameter"] == "Flow Rate"
    )
    target_pressure = next(
        r for r in modified
        if r["asset_id"] == "C1-P-001" and r["parameter"] == "Pressure"
    )
    assert target_flow["value"] < 100.0
    assert target_pressure["value"] < 50.0

    # Non-target asset: unchanged.
    other_flow = next(
        r for r in modified
        if r["asset_id"] == "C1-P-002" and r["parameter"] == "Flow Rate"
    )
    other_pressure = next(
        r for r in modified
        if r["asset_id"] == "C1-P-002" and r["parameter"] == "Pressure"
    )
    assert other_flow["value"] == 100.0
    assert other_pressure["value"] == 50.0


def test_no_active_events_returns_baseline_unchanged(
    running_generator, monkeypatch
):
    """With no active events, generate() must return the frozen baseline
    exactly — identical values, not merely matching schema and count."""
    import copy
    from simulator.generators import operational

    fixed_baseline = [
        {
            "sensor_id": "C1-P-001-FLOW",
            "asset_id": "C1-P-001",
            "parameter": "Flow Rate",
            "value": 100.0,
            "unit": "L/min",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "sensor_id": "C1-P-001-PRESSURE",
            "asset_id": "C1-P-001",
            "parameter": "Pressure",
            "value": 50.0,
            "unit": "PSI",
            "timestamp": "2024-01-01T00:00:00",
        },
    ]
    monkeypatch.setattr(
        operational,
        "get_normal_readings",
        lambda: copy.deepcopy(fixed_baseline),
    )

    readings = running_generator.generate()
    assert readings == fixed_baseline, (
        "with no active events, generate() must return the baseline unchanged"
    )


def test_deactivated_leak_returns_to_baseline(running_generator, monkeypatch):
    """After deactivating a leak, generate() must return the frozen
    baseline exactly — identical to the pre-event state."""
    import copy
    from simulator.generators import operational

    fixed_baseline = [
        {
            "sensor_id": "C1-P-001-FLOW",
            "asset_id": "C1-P-001",
            "parameter": "Flow Rate",
            "value": 100.0,
            "unit": "L/min",
            "timestamp": "2024-01-01T00:00:00",
        },
        {
            "sensor_id": "C1-P-001-PRESSURE",
            "asset_id": "C1-P-001",
            "parameter": "Pressure",
            "value": 50.0,
            "unit": "PSI",
            "timestamp": "2024-01-01T00:00:00",
        },
    ]
    monkeypatch.setattr(
        operational,
        "get_normal_readings",
        lambda: copy.deepcopy(fixed_baseline),
    )

    # Activate leak and confirm it changes the readings.
    running_generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    running_generator.activate_event("leak-1")
    with_leak = running_generator.generate()
    assert with_leak != fixed_baseline, "active leak must modify readings"

    # Deactivate and confirm the baseline is restored exactly.
    running_generator.deactivate_event("leak-1")
    after_deactivation = running_generator.generate()
    assert after_deactivation == fixed_baseline, (
        "deactivation must restore the frozen baseline exactly"
    )


def test_multiple_events_apply_together(running_generator):
    running_generator.register_event("leak", "leak-1", "C1-P-001", 0.5)
    running_generator.register_event("leak", "leak-2", "C1-P-002", 0.5)
    running_generator.activate_event("leak-1")
    running_generator.activate_event("leak-2")

    readings = running_generator.generate()
    assert len(readings) == EXPECTED_READINGS
    assert all(set(r.keys()) == READING_KEYS for r in readings)


def test_all_six_event_types_can_be_activated_and_applied(running_generator):
    cases = [
        ("leak",          "C1-P-001"),
        ("deterioration", "C1-P-002"),
        ("pressure_drop", "C1-P-003"),
        ("pump_failure",  "C1-PS-001"),
        ("valve_failure", "C1-V-001"),
        ("water_quality", "C1-R-001"),
    ]
    for i, (etype, aid) in enumerate(cases):
        running_generator.register_event(etype, f"ev-{i}", aid, 0.3)
        running_generator.activate_event(f"ev-{i}")

    readings = running_generator.generate()
    assert len(readings) == EXPECTED_READINGS
    assert all(set(r.keys()) == READING_KEYS for r in readings)


# ----------------------------------------------------------------------
# Full backend-facing workflow
# ----------------------------------------------------------------------

def test_full_workflow(fresh_city):
    """The exact sequence the backend will run."""
    gen = SimulationGenerator()

    # 1. Idle -> start
    assert gen.state == SimulationState.IDLE
    gen.start()
    assert gen.state == SimulationState.RUNNING

    # 2. Baseline generation
    baseline = gen.generate()
    assert len(baseline) == EXPECTED_READINGS
    assert gen.tick == 1

    # 3. Register and activate a leak
    gen.register_event("leak", "leak-1", "C1-P-001", 0.5)
    gen.activate_event("leak-1")

    # 4. Generate with leak applied
    modified = gen.generate()
    assert len(modified) == EXPECTED_READINGS
    assert gen.tick == 2

    # 5. Pause -> generate should fail
    gen.pause()
    with pytest.raises(RuntimeError):
        gen.generate()

    # 6. Resume -> generate works again
    gen.resume()
    readings = gen.generate()
    assert len(readings) == EXPECTED_READINGS
    assert gen.tick == 3

    # 7. Stop -> generate should fail
    gen.stop()
    with pytest.raises(RuntimeError):
        gen.generate()

    # 8. Reset -> back to IDLE, events cleared
    gen.reset()
    assert gen.state == SimulationState.IDLE
    assert gen.tick == 0
    assert gen.list_events() == []

    # 9. Restart from IDLE
    gen.start()
    assert gen.state == SimulationState.RUNNING
    readings = gen.generate()
    assert len(readings) == EXPECTED_READINGS
    assert gen.tick == 1