"""
leaks.py - Collection manager for multiple LeakEvent objects.

Purpose
-------
A small, in-memory collection of LeakEvent instances keyed by event_id.

    leak.py    -> one LeakEvent
    leaks.py   -> many LeakEvent objects (this file)
    event_manager.py -> complete event layer coordinator

Design
------
- Standalone. This module does NOT import EventManager.
- Keyed by event_id. Duplicate event IDs are rejected.
- All lifecycle and effect logic is delegated to the stored LeakEvent
  objects. This file does not duplicate leak calculation.
- Reading schema is preserved exactly. No event metadata is added to
  readings. No upstream/downstream propagation.

Relationship with EventManager
------------------------------
EventManager already keeps its own registry of generic events.
Leaks is a specialized collection for leak events only.

Pick one of the following patterns per use case:

    Pattern A - Leaks alone:
        leaks = Leaks()
        leaks.add(LeakEvent(...))
        readings = leaks.apply_active(readings, ASSETS)

    Pattern B - LeakEvents registered individually with EventManager:
        manager = EventManager(assets_by_id=ASSETS)
        for leak in some_leaks:
            manager.register_event(leak)
        readings = manager.apply_events(readings)

Do not add the same LeakEvent object to both a Leaks collection and
an EventManager. If both are used, one source of truth must be chosen
so that a leak is not applied twice.

Frozen reading schema:

    {
        "sensor_id": str,
        "asset_id": str,
        "parameter": str,
        "value": float | str,
        "unit": str,
        "timestamp": str
    }
"""

from typing import Any, Dict, List, Optional

from simulator.events.leak import LeakEvent


class Leaks:
    """
    Simple, in-memory collection of LeakEvent objects.

    All methods that change state or return event lists preserve
    insertion order of the underlying dictionary.
    """

    # Minimal duck-typed contract every stored event must satisfy.
    REQUIRED_ATTRS = ("event_id", "asset_id", "active")
    REQUIRED_METHODS = ("activate", "deactivate", "apply")

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._leaks: Dict[str, LeakEvent] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def add(self, leak: LeakEvent) -> LeakEvent:
        """
        Add a leak event to the collection.

        The event is stored by its event_id. Duplicate event IDs are
        rejected with ValueError. Returns the stored event for chaining.
        """
        self._validate_leak_object(leak)

        event_id = leak.event_id
        if event_id in self._leaks:
            raise ValueError(f"Leak already registered: {event_id}")

        self._leaks[event_id] = leak
        return leak

    def remove(self, event_id: str) -> bool:
        """
        Remove a leak by event_id.

        Raises KeyError if the event_id is unknown.
        """
        self._get_or_raise(event_id)
        del self._leaks[event_id]
        return True

    def clear(self) -> None:
        """
        Deactivate every stored leak and empty the collection.
        """
        for leak in self._leaks.values():
            leak.deactivate()
        self._leaks.clear()

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, event_id: str) -> Optional[LeakEvent]:
        """Return the leak for event_id, or None if unknown."""
        return self._leaks.get(event_id)

    def has(self, event_id: str) -> bool:
        """Return True if a leak with this event_id is stored."""
        return event_id in self._leaks

    def all(self) -> List[LeakEvent]:
        """Return all stored leaks in insertion order."""
        return list(self._leaks.values())

    def active(self) -> List[LeakEvent]:
        """Return only the stored leaks that are currently active."""
        return [leak for leak in self._leaks.values() if leak.active]

    def for_asset(self, asset_id: str) -> List[LeakEvent]:
        """Return all stored leaks targeting the given asset."""
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("asset_id must be a non-empty string.")
        return [leak for leak in self._leaks.values() if leak.asset_id == asset_id]

    def count(self) -> int:
        """Return the total number of stored leaks."""
        return len(self._leaks)

    def active_count(self) -> int:
        """Return the number of currently active leaks."""
        return len(self.active())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self, event_id: str) -> bool:
        """Activate a stored leak. Raises KeyError if unknown."""
        leak = self._get_or_raise(event_id)
        leak.activate()
        return True

    def deactivate(self, event_id: str) -> bool:
        """Deactivate a stored leak. Raises KeyError if unknown."""
        leak = self._get_or_raise(event_id)
        leak.deactivate()
        return True

    def activate_all(self) -> None:
        """Activate every stored leak."""
        for leak in self._leaks.values():
            leak.activate()

    def deactivate_all(self) -> None:
        """Deactivate every stored leak."""
        for leak in self._leaks.values():
            leak.deactivate()

    # ------------------------------------------------------------------
    # Effect application
    # ------------------------------------------------------------------

    def apply_active(
        self,
        readings: List[Dict[str, Any]],
        assets_by_id: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Apply every active leak to the given readings.

        Delegates to LeakEvent.apply(readings, assets_by_id) for each
        active leak, in insertion order. Each event receives the output
        of the previous one.

        Returns a new list of readings. The caller's list is not
        modified in place. The frozen reading schema is preserved.
        """
        if not isinstance(readings, list):
            raise ValueError("readings must be a list of dictionaries.")

        result = list(readings)

        for leak in self.active():
            new_result = leak.apply(result, assets_by_id)
            if not isinstance(new_result, list):
                raise ValueError(
                    f"Leak {leak.event_id} apply() must return a list."
                )
            result = new_result

        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> List[Dict[str, Any]]:
        """
        Return a JSON-friendly status list for every stored leak.

        Uses LeakEvent.to_dict() when available, otherwise falls back
        to a small, predictable set of fields.
        """
        status: List[Dict[str, Any]] = []

        for leak in self._leaks.values():
            to_dict = getattr(leak, "to_dict", None)
            if callable(to_dict):
                status.append(to_dict())
                continue

            status.append({
                "event_id": getattr(leak, "event_id", None),
                "event_type": getattr(leak, "event_type", None),
                "asset_id": getattr(leak, "asset_id", None),
                "severity": getattr(leak, "severity", None),
                "active": bool(getattr(leak, "active", False)),
                "start_time": getattr(leak, "start_time", None),
            })

        return status

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Leaks(total={self.count()}, active={self.active_count()})"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_raise(self, event_id: str) -> LeakEvent:
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string.")
        if event_id not in self._leaks:
            raise KeyError(f"Unknown leak event_id: {event_id}")
        return self._leaks[event_id]

    def _validate_leak_object(self, leak: Any) -> None:
        """
        Minimal duck-typed contract check.

        LeakEvent's own validation (severity, asset type, asset existence)
        is not duplicated here. That belongs to LeakEvent and is applied
        when the leak is constructed and when it is used with an
        EventManager.
        """
        if leak is None:
            raise ValueError("leak must not be None.")

        if not isinstance(leak, LeakEvent):
            raise ValueError(
                f"leaks.py only accepts LeakEvent objects, got "
                f"{type(leak).__name__}."
            )

        for attr in self.REQUIRED_ATTRS:
            if not hasattr(leak, attr):
                raise ValueError(f"LeakEvent is missing attribute: {attr}")

        for method in self.REQUIRED_METHODS:
            fn = getattr(leak, method, None)
            if not callable(fn):
                raise ValueError(f"LeakEvent is missing method: {method}")

        if not isinstance(leak.event_id, str) or not leak.event_id.strip():
            raise ValueError("LeakEvent event_id must be a non-empty string.")

        if not isinstance(leak.asset_id, str) or not leak.asset_id.strip():
            raise ValueError("LeakEvent asset_id must be a non-empty string.")