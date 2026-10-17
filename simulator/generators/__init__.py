"""Generator layer for the AquaShield AI simulator.

This package is the public API for the backend and any higher-level
caller. It coordinates the existing city, sensor, and event layers
without duplicating their logic.

Public API
----------
SimulationGenerator
    Lifecycle coordinator. Owns simulation state, tick counter, and
    event management. Used by the backend to start, pause, resume,
    stop, reset, and generate readings.

SimulationState
    Enum of lifecycle states: IDLE, RUNNING, PAUSED, STOPPED.
    Returned by SimulationGenerator.state.

Typical usage:

    from simulator.city.virtual_city import create_virtual_city
    from simulator.generators import SimulationGenerator

    create_virtual_city()
    gen = SimulationGenerator()
    gen.start()
    readings = gen.generate()          # 328 readings, tick = 1

    gen.register_event("leak", "leak-1", "C1-P-001", 0.5)
    gen.activate_event("leak-1")
    readings = gen.generate()          # 328 readings, leak applied

    gen.stop()
    gen.reset()

Importing this package performs no work. It does not create a
virtual city, initialize sensors, generate readings, register
events, or create any global state. All work happens when the
caller invokes methods on a SimulationGenerator instance.

Internal modules (not part of the public API):

    sensor_data.py   thin adapter over simulator.sensors
    normal_data.py   baseline reading source (no events applied)
    event_data.py    applies active events to baseline readings
    operational.py   SimulationGenerator and SimulationState
    demand.py        documented stub (demand generation is deferred)

Callers that need the reading schema should treat readings as plain
dicts with the frozen six fields:

    {
        "sensor_id": str,
        "asset_id": str,
        "parameter": str,
        "value": float | str,
        "unit": str,
        "timestamp": str
    }
"""

from simulator.generators.operational import (
    SimulationGenerator,
    SimulationState,
)


__all__ = [
    "SimulationGenerator",
    "SimulationState",
]