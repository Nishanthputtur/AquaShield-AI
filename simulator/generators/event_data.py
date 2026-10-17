"""Apply active virtual events to baseline sensor readings.

This module is the "modified readings" stage of the generator layer.
It takes a baseline reading cycle (from normal_data.py) and applies
all currently active events through EventManager.

It does not:

    - generate readings itself
    - create or register events
    - modify sensor objects or assets
    - perform analytics, scoring, or persistence
    - know which concrete event classes exist

All event-processing logic lives in the event layer (simulator.events).
This module is a thin adapter that names the intent: "apply events
to these readings and give me back the result".

Typical usage:

    from simulator.city.virtual_city import create_virtual_city
    from simulator.generators.normal_data import get_normal_readings
    from simulator.generators.event_data import apply_active_events
    from simulator.events import EventManager, LeakEvent

    create_virtual_city()
    baseline = get_normal_readings()

    manager = EventManager(assets_by_id=ASSETS)
    manager.register_event(LeakEvent(
        event_id="leak-1",
        asset_id="C1-P-001",
        severity=0.4,
    ))
    manager.activate_event("leak-1")

    modified = apply_active_events(baseline, manager)
"""

from typing import TypeAlias

from simulator.events import EventManager


# Frozen reading schema used throughout the simulator.
#
#   {
#       "sensor_id": str,
#       "asset_id": str,
#       "parameter": str,
#       "value": float | str,
#       "unit": str,
#       "timestamp": str
#   }
SensorReading: TypeAlias = dict[str, str | float]


def apply_active_events(
    readings: list[SensorReading],
    event_manager: EventManager,
) -> list[SensorReading]:
    """Apply all currently active events and return the resulting readings.

    Arguments:
        readings: A baseline list of reading dicts, typically the output
            of normal_data.get_normal_readings(). Must be a list of
            reading dicts with the frozen six-field schema.
        event_manager: An EventManager instance holding registered
            events. Only events whose `active` flag is True are applied.
            Inactive events are ignored.

    Returns:
        A new list of reading dicts with the same six-field schema.
        The input list is not modified. The length is unchanged: events
        alter values, they never add or remove readings.

    If the event_manager has no active events, the returned list is
    equal in content to the input list (event_manager.apply_events
    behaves as an identity operation).
    """
    return event_manager.apply_events(readings)