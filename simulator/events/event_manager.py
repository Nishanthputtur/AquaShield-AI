"""
event_manager.py - Central coordinator for the AquaShield AI event layer.

The manager stores event objects in memory, tracks which of them are
currently active, and applies their effects to a list of sensor readings.

It is deliberately generic. It does not import any specific event class
(LeakEvent, PumpFailureEvent, ...). It works with any object that
satisfies this simple contract:

    event.event_id              -> str, unique identifier
    event.asset_id              -> str, the target asset
    event.active                -> bool, current active state
    event.activate()            -> mark active
    event.deactivate()          -> mark inactive
    event.apply(readings, assets_by_id) -> new list[dict] of readings

Optional attributes, used when present:

    event.expected_asset_type   -> AssetType, for target validation
    event.event_type            -> str, for status output
    event.severity              -> float, for status output
    event.validate(assets_by_id) -> custom validation hook
    event.to_dict()             -> dict, richer status output

Design rules:

- Per-asset events. No upstream/downstream propagation.
- Reading dictionaries keep the frozen schema. No event metadata is
  added to readings.
- No analytics, scoring, database, backend, or frontend access.
- No globals, no threads, no timers, no background loops.
- State lives in the manager instance and in event objects.

Example usage:

    from simulator.city.virtual_city import create_virtual_city
    from simulator.city.assets import ASSETS
    from simulator.sensors import initialize_sensors, generate_all_readings
    from simulator.events.event_manager import EventManager

    create_virtual_city()
    initialize_sensors()

    manager = EventManager(assets_by_id=ASSETS)
    manager.register_event(LeakEvent(event_id="leak-1", asset_id="C1-P-001",severity=0.4))
    manager.activate_event("leak-1")

    readings = generate_all_readings()
    readings = manager.apply_events(readings)
"""

from typing import Any, Dict, List, Optional


class EventManager:
    """
    Coordinates a set of event objects and applies their effects.

    The manager never modifies events or readings directly.
    It only:

    - stores events by event_id,
    - toggles their active state,
    - calls event.apply(readings, assets_by_id) for every active event
      in registration order,
    - returns the final list of readings.
    """

    # Attributes every event object must expose.
    REQUIRED_EVENT_ATTRS = ("event_id", "asset_id", "active")

    # Methods every event object must expose.
    REQUIRED_EVENT_METHODS = ("activate", "deactivate", "apply")

    def __init__(self, assets_by_id: Dict[str, Any]) -> None:
        """
        Parameters
        ----------
        assets_by_id:
            A dict mapping asset_id -> Asset. Typically the existing
            simulator.city.assets.ASSETS dictionary.
        """
        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        self.assets_by_id: Dict[str, Any] = assets_by_id

        # Internal in-memory registry.
        # Maps event_id -> event object.
        self._events: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Registration and lookup
    # ------------------------------------------------------------------

    def register_event(self, event: Any) -> Any:
        """
        Register an event object.

        Validates the event contract, checks the target asset, and
        rejects duplicate event_id values.
        """
        self._validate_event_object(event)

        event_id = event.event_id
        if event_id in self._events:
            raise ValueError(f"Event already registered: {event_id}")

        self._validate_target(event)

        self._events[event_id] = event
        return event

    def remove_event(self, event_id: str) -> bool:
        """Remove a registered event by event_id."""
        self._get_event_or_raise(event_id)
        del self._events[event_id]
        return True

    def get_event(self, event_id: str) -> Optional[Any]:
        """Return the event object for event_id, or None if unknown."""
        return self._events.get(event_id)

    def has_event(self, event_id: str) -> bool:
        """Return True if an event with this event_id is registered."""
        return event_id in self._events

    def is_active(self, event_id: str) -> bool:
        """Return True if the given event is currently active."""
        event = self._get_event_or_raise(event_id)
        return bool(getattr(event, "active", False))

    # ------------------------------------------------------------------
    # Activation
    # ------------------------------------------------------------------

    def activate_event(self, event_id: str) -> bool:
        """
        Activate a registered event.

        Calls event.activate() so the event can run its own checks.
        The manager also re-validates the target so that removed or
        replaced assets do not silently break later.
        """
        event = self._get_event_or_raise(event_id)

        self._validate_target(event)

        activate = getattr(event, "activate", None)
        if callable(activate):
            activate()
        else:
            event.active = True

        return True

    def deactivate_event(self, event_id: str) -> bool:
        """Deactivate a registered event."""
        event = self._get_event_or_raise(event_id)

        deactivate = getattr(event, "deactivate", None)
        if callable(deactivate):
            deactivate()
        else:
            event.active = False

        return True

    def get_active_events(self) -> List[Any]:
        """Return the list of currently active events."""
        return [
            event
            for event in self._events.values()
            if getattr(event, "active", False)
        ]

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_events(self) -> None:
        """
        Deactivate every registered event and clear the registry.

        After this call the manager has no events and no active state.
        """
        for event in self._events.values():
            deactivate = getattr(event, "deactivate", None)
            if callable(deactivate):
                deactivate()
            else:
                event.active = False

        self._events.clear()

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------

    def apply_events(self, readings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply every active event to the given readings.

        The input list is not mutated. Each active event receives the
        output of the previous one, in registration order. The final
        list is returned to the caller.

        Each event.apply(...) must return a list of readings with the
        frozen schema:

            {
                "sensor_id": str,
                "asset_id": str,
                "parameter": str,
                "value": float | str,
                "unit": str,
                "timestamp": str
            }
        """
        if not isinstance(readings, list):
            raise ValueError("readings must be a list of dictionaries.")

        result = list(readings)

        for event in self.get_active_events():
            new_result = event.apply(result, self.assets_by_id)

            if not isinstance(new_result, list):
                raise ValueError(
                    f"Event {event.event_id} apply() must return a list."
                )

            result = new_result

        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_event_status(self) -> List[Dict[str, Any]]:
        """
        Return a simple, JSON-friendly status list for all events.

        Uses event.to_dict() when available, otherwise falls back to
        a small, predictable set of fields.
        """
        status: List[Dict[str, Any]] = []

        for event in self._events.values():
            to_dict = getattr(event, "to_dict", None)
            if callable(to_dict):
                status.append(to_dict())
                continue

            status.append({
                "event_id": getattr(event, "event_id", None),
                "asset_id": getattr(event, "asset_id", None),
                "event_type": getattr(event, "event_type", None),
                "severity": getattr(event, "severity", None),
                "active": bool(getattr(event, "active", False)),
            })

        return status

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_event_or_raise(self, event_id: str) -> Any:
        if event_id not in self._events:
            raise KeyError(f"Unknown event_id: {event_id}")
        return self._events[event_id]

    def _validate_event_object(self, event: Any) -> None:
        """Check the minimal event contract. Raises ValueError on failure."""

        if event is None:
            raise ValueError("event must not be None.")

        for attr in self.REQUIRED_EVENT_ATTRS:
            if not hasattr(event, attr):
                raise ValueError(f"Event is missing required attribute: {attr}")

        for method in self.REQUIRED_EVENT_METHODS:
            fn = getattr(event, method, None)
            if not callable(fn):
                raise ValueError(f"Event is missing required method: {method}")

        if not isinstance(event.event_id, str) or not event.event_id.strip():
            raise ValueError("Event event_id must be a non-empty string.")

        if not isinstance(event.asset_id, str) or not event.asset_id.strip():
            raise ValueError("Event asset_id must be a non-empty string.")

    def _validate_target(self, event: Any) -> None:
        """
        Validate the event's target asset.

        First gives the event a chance to run its own validate() hook
        (used by events with asset-type-specific rules). Then performs
        the generic checks that apply to every event.
        """

        # Let the event do its own validation when it wants to.
        validator = getattr(event, "validate", None)
        if callable(validator):
            validator(self.assets_by_id)

        asset_id = getattr(event, "asset_id", None)
        if asset_id is None:
            return

        if asset_id not in self.assets_by_id:
            raise ValueError(f"Event target asset not found: {asset_id}")

        expected_type = getattr(event, "expected_asset_type", None)
        if expected_type is not None:
            asset = self.assets_by_id[asset_id]
            actual_type = getattr(asset, "asset_type", None)

            if actual_type != expected_type:
                raise ValueError(
                    f"Event {event.event_id} expects asset type "
                    f"{expected_type}, but {asset_id} is {actual_type}."
                )