"""
simulator.events package.

Public event-layer API for AquaShield AI.

The event layer introduces abnormal operating conditions into the
virtual water infrastructure simulation. It operates on the readings
produced by simulator.sensors and produces modified readings that
simulator.analytics can later interpret.

Architecture
------------
    city/       defines assets
    sensors/    produces normal readings
    events/     introduces abnormal conditions (this package)
    analytics/  interprets abnormal readings

Design rules
------------
- Events are per-asset. No upstream/downstream propagation.
- Events modify reading dictionaries only. Sensor classes are not
  modified and Asset objects are not modified.
- Event modules do not import EventManager. EventManager coordinates
  the event modules.
- No analytics, scoring, database, backend, or frontend logic lives
  in this package.
- No simulation work happens at import time. Importing this package
  only exposes the public classes; it does not create assets, sensors,
  events, readings, timers, threads, schedulers, or background work.

Reading schema (frozen, never modified structurally):

    {
        "sensor_id": str,
        "asset_id": str,
        "parameter": str,
        "value": float | str,
        "unit": str,
        "timestamp": str
    }

Typical usage:

    from simulator.events import (
        EventManager,
        LeakEvent,
        DeteriorationEvent,
    )

    manager = EventManager(assets_by_id=ASSETS)
    manager.register_event(LeakEvent(event_id="leak-1",
                                     asset_id="C1-P-001",
                                     severity=0.4))
    manager.activate_event("leak-1")
    modified = manager.apply_events(readings)
"""

from .event_manager import EventManager
from .leak import LeakEvent
from .leaks import Leaks
from .deterioration import DeteriorationEvent
from .pressure_drop import PressureDropEvent
from .pump_failure import PumpFailureEvent
from .valve_failure import ValveFailureEvent
from .water_quality import WaterQualityEvent


__all__ = [
    "EventManager",
    "LeakEvent",
    "Leaks",
    "DeteriorationEvent",
    "PressureDropEvent",
    "PumpFailureEvent",
    "ValveFailureEvent",
    "WaterQualityEvent",
]