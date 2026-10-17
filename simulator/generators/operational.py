"""Simulation lifecycle and public generator interface for AquaShield AI.

This module owns the complete workflow of the generator layer:

    1. A caller creates the virtual city (ASSETS is populated).
    2. A caller creates one SimulationGenerator.
    3. The caller controls the simulation through start / pause /
       resume / stop / reset.
    4. Readings are produced only while state == RUNNING. Each
       successful generate() advances the tick by exactly 1.
    5. Events are registered and controlled through neutral methods
       (register_event / activate_event / deactivate_event). The
       backend never imports concrete event classes or EventManager.

Strict lifecycle (invalid transitions raise RuntimeError):

    Operation  | Required state      | Result
    -----------+---------------------+--------------------------------
    start      | IDLE                | RUNNING, tick = 0
    pause      | RUNNING             | PAUSED
    resume     | PAUSED              | RUNNING
    stop       | RUNNING or PAUSED   | STOPPED (tick and events kept)
    reset      | any                 | IDLE, tick = 0, events cleared
    generate   | RUNNING             | readings; tick += 1 on success

    Starting again after stop requires reset().

A failed generate() (raised exception) does not advance the tick.

The generator coordinates existing components. It does not contain
sensor-generation logic, event logic, or analytics.
"""

from enum import Enum
from typing import Optional

from simulator.events import (
    DeteriorationEvent,
    EventManager,
    LeakEvent,
    PressureDropEvent,
    PumpFailureEvent,
    ValveFailureEvent,
    WaterQualityEvent,
)

from simulator.generators.event_data import apply_active_events
from simulator.generators.normal_data import get_normal_readings
from simulator.generators.sensor_data import SensorReading


class SimulationState(Enum):
    """Lifecycle states for the virtual simulation."""

    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


def _build_event(
    event_type: str,
    event_id: str,
    asset_id: str,
    severity: float,
):
    """Construct a concrete event object for the neutral event_type name.

    Raises ValueError for unknown event_type values. Any ValueError
    raised by the event constructor (for example, wrong target asset
    type or out-of-range severity) propagates to the caller.
    """
    if event_type == "leak":
        return LeakEvent(
            event_id=event_id,
            asset_id=asset_id,
            severity=severity,
        )

    if event_type == "deterioration":
        # DeteriorationEvent does not accept severity. It uses its own
        # initial_level and default_step to model gradual degradation.
        # severity is validated at the generator boundary for interface
        # consistency, but is not passed to this event class.
        return DeteriorationEvent(
            event_id=event_id,
            asset_id=asset_id,
        )

    if event_type == "pressure_drop":
        return PressureDropEvent(
            event_id=event_id,
            asset_id=asset_id,
            severity=severity,
        )

    if event_type == "pump_failure":
        return PumpFailureEvent(
            event_id=event_id,
            asset_id=asset_id,
            severity=severity,
        )

    if event_type == "valve_failure":
        return ValveFailureEvent(
            event_id=event_id,
            asset_id=asset_id,
            severity=severity,
        )

    if event_type == "water_quality":
        return WaterQualityEvent(
            event_id=event_id,
            asset_id=asset_id,
            severity=severity,
        )

    raise ValueError(
        f"Unknown event_type {event_type!r}. "
        f"Valid types: ['deterioration', 'leak', 'pressure_drop', "
        f"'pump_failure', 'valve_failure', 'water_quality']"
    )


class SimulationGenerator:
    """Coordinates the virtual simulation lifecycle and readings.

    One instance per running simulation. Owns its own EventManager,
    its own state, and its own tick counter. Constructs no global
    state and performs no work until the caller invokes a method.

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
    """

    def __init__(self, assets_by_id: Optional[dict] = None) -> None:
        """Create a generator in the IDLE state with tick = 0.

        Arguments:
            assets_by_id: Optional asset_id -> Asset mapping.
                If omitted, the module-level ASSETS registry is used.
                The caller must create the virtual city before calling
                generate(), so that ASSETS is populated.
        """
        if assets_by_id is None:
            # Lazy import: avoids importing simulator.city at module load,
            # which keeps the generators package light and cycle-free.
            from simulator.city.assets import ASSETS
            assets_by_id = ASSETS

        self._assets_by_id = assets_by_id
        self._event_manager = EventManager(assets_by_id=assets_by_id)
        self._state = SimulationState.IDLE
        self._tick = 0

    # ------------------------------------------------------------------
    # Public read-only state
    # ------------------------------------------------------------------

    @property
    def state(self) -> SimulationState:
        """Current simulation state."""
        return self._state

    @property
    def tick(self) -> int:
        """Number of successfully generated reading cycles."""
        return self._tick

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start a fresh simulation from tick 0.

        Requires: state == IDLE.
        After stop(), call reset() before starting again.
        """
        if self._state != SimulationState.IDLE:
            raise RuntimeError(
                f"Cannot start: state is {self._state.value}, "
                f"expected IDLE. Use reset() first."
            )
        self._state = SimulationState.RUNNING
        self._tick = 0

    def pause(self) -> None:
        """Pause the running simulation without losing state.

        Requires: state == RUNNING.
        """
        if self._state != SimulationState.RUNNING:
            raise RuntimeError(
                f"Cannot pause: state is {self._state.value}, "
                f"expected RUNNING."
            )
        self._state = SimulationState.PAUSED

    def resume(self) -> None:
        """Resume from a paused state.

        Requires: state == PAUSED.
        """
        if self._state != SimulationState.PAUSED:
            raise RuntimeError(
                f"Cannot resume: state is {self._state.value}, "
                f"expected PAUSED."
            )
        self._state = SimulationState.RUNNING

    def stop(self) -> None:
        """Stop the simulation, preserving tick and registered events.

        Requires: state == RUNNING or PAUSED.
        After stop(), state becomes STOPPED. Generating readings is
        not possible until reset() is called and start() runs again.
        """
        if self._state not in (SimulationState.RUNNING, SimulationState.PAUSED):
            raise RuntimeError(
                f"Cannot stop: state is {self._state.value}, "
                f"expected RUNNING or PAUSED."
            )
        self._state = SimulationState.STOPPED

    def reset(self) -> None:
        """Return to IDLE, clear tick, and clear all registered events.

        Allowed from any state. This is the only way to leave STOPPED
        and the only way to clear registered events.
        """
        self._state = SimulationState.IDLE
        self._tick = 0
        self._event_manager.reset_events()

    # ------------------------------------------------------------------
    # Reading generation
    # ------------------------------------------------------------------

    def generate(self) -> list[SensorReading]:
        """Produce one reading cycle with active events applied.

        Requires: state == RUNNING.

        Steps:
            1. Produce baseline readings via get_normal_readings().
               This initializes sensors on first call (idempotent).
            2. Apply all active events via apply_active_events().
            3. Increment tick by exactly 1.

        Returns:
            A new list of reading dicts with the frozen six-field
            schema. Exactly 328 readings are returned when the virtual
            city contains 108 assets.

        Raises:
            RuntimeError: if state is not RUNNING.
            Any exception raised by reading generation or event
            processing propagates; the tick is not advanced.
        """
        if self._state != SimulationState.RUNNING:
            raise RuntimeError(
                f"Cannot generate readings: state is {self._state.value}, "
                f"expected RUNNING."
            )

        baseline = get_normal_readings()
        modified = apply_active_events(baseline, self._event_manager)
        self._tick += 1
        return modified

    # ------------------------------------------------------------------
    # Event registration and control
    # ------------------------------------------------------------------

    def register_event(
        self,
        event_type: str,
        event_id: str,
        asset_id: str,
        severity: float,
    ) -> None:
        """Register an event of the given type without activating it.

        Arguments:
            event_type: One of "leak", "deterioration", "pressure_drop",
                "pump_failure", "valve_failure", "water_quality".
            event_id:   Unique event identifier.
            asset_id:   Target asset identifier, e.g. "C1-P-001".
            severity:   Float in [0.0, 1.0].

        The concrete event class validates its own target (for example,
        PumpFailureEvent rejects non-pump assets). Any such exception
        propagates, and no event is registered on failure.

        Note: DeteriorationEvent does not accept severity; it uses its
        own class-level defaults for gradual degradation. Severity is
        still validated here for interface consistency.

        Raises:
            ValueError: if event_type is not a known event type, if
                severity is not a number in [0.0, 1.0], or if the
                concrete event class rejects its target.
        """
        if not isinstance(severity, (int, float)):
            raise ValueError(
                f"severity must be a number, got {type(severity).__name__}."
            )
        if not (0.0 <= severity <= 1.0):
            raise ValueError(
                f"severity must be in [0.0, 1.0], got {severity}."
            )

        event = _build_event(event_type, event_id, asset_id, severity)
        self._event_manager.register_event(event)

    def activate_event(self, event_id: str) -> None:
        """Activate a registered event so generate() applies it."""
        self._event_manager.activate_event(event_id)

    def deactivate_event(self, event_id: str) -> None:
        """Deactivate a registered event so generate() ignores it.

        The event remains registered and can be activated again.
        """
        self._event_manager.deactivate_event(event_id)

    def list_events(self) -> list[dict]:
        """Return summaries of all registered events.

        Each summary is a plain dict produced by the event's to_dict(),
        with fields such as event_id, asset_id, event_type, severity,
        and active. Used by the backend to display event state without
        importing concrete event classes or EventManager.
        """
        return self._event_manager.get_event_status()

    # ------------------------------------------------------------------
    # Debugging
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SimulationGenerator(state={self._state.value}, "
            f"tick={self._tick})"
        )