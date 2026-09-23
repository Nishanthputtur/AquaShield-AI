"""
deterioration.py - Gradual asset deterioration event for AquaShield AI.

Purpose
-------
Represents slow degradation of one asset over simulation steps.

Unlike LeakEvent (sudden loss of flow and pressure), DeteriorationEvent
produces a gradual, controlled drift in the asset's numeric readings
as its deterioration_level rises from 0.0 to 1.0.

Design
------
- One event targets one asset.
- Supported asset types: PIPELINE, PUMP_STATION, VALVE.
- The event stores a normalized deterioration level in [0.0, 1.0].
- apply() is a pure function of (input readings, current level).
  It does not compound itself. The caller is responsible for passing
  fresh normal readings to EventManager each simulation step.
- No analytics, no scoring, no database, no frontend, no generators.
- No threads, no timers, no background loops.

Compatible with simulator/events/event_manager.py:

- Attributes : event_id, asset_id, active, deterioration_level
- Methods    : activate(), deactivate(), apply(readings, assets_by_id),
               validate(assets_by_id), to_dict()
- Extra      : advance(step=None), set_level(level), reset()

Note: expected_asset_type is intentionally NOT defined as a class
attribute. Multiple asset types are valid, and EventManager's
_validate_target only checks a single expected type. Type validation
is done inside validate() instead.

Frozen reading schema (never modified structurally):

    {
        "sensor_id": str,
        "asset_id": str,
        "parameter": str,
        "value": float | str,
        "unit": str,
        "timestamp": str
    }

Only numeric "value" fields of the target asset's affected parameters
are changed. Everything else is passed through unchanged.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from simulator.city.assets import AssetType


class DeteriorationEvent:
    """
    Gradual degradation event for one asset.

    Supported asset types and affected parameters:

        Pipeline       : Pressure, Flow Rate
        Pump Station   : Pressure, Flow Rate, Temperature,
                         Vibration, Power Consumption
        Valve          : Pressure, Flow Rate, Valve Position

    Effects scale linearly with deterioration_level:

        level = 0.0  -> readings unchanged
        level = 1.0  -> maximum configured effect

    Direction of change per parameter:

        Pressure               decreases
        Flow Rate              decreases
        Temperature            increases
        Vibration              increases
        Power Consumption      increases
        Valve Position         decreases

    No string parameters (Equipment Status) are modified.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    event_type: str = "deterioration"

    SUPPORTED_ASSET_TYPES = (
        AssetType.PIPELINE,
        AssetType.PUMP_STATION,
        AssetType.VALVE,
    )

    # Parameters the event is allowed to modify, per asset type.
    AFFECTED_PARAMETERS: Dict[AssetType, set] = {
        AssetType.PIPELINE: {"Pressure", "Flow Rate"},
        AssetType.PUMP_STATION: {
            "Pressure",
            "Flow Rate",
            "Temperature",
            "Vibration",
            "Power Consumption",
        },
        AssetType.VALVE: {"Pressure", "Flow Rate", "Valve Position"},
    }

    # Maximum fractional change at deterioration_level = 1.0.
    # Each is applied as: new = old * (1 +/- factor * level)
    MAX_PRESSURE_REDUCTION: float = 0.25
    MAX_FLOW_REDUCTION: float = 0.20
    MAX_TEMPERATURE_INCREASE: float = 0.30
    MAX_VIBRATION_INCREASE: float = 0.80
    MAX_POWER_INCREASE: float = 0.25
    MAX_VALVE_POSITION_REDUCTION: float = 0.30

    # Default step used by advance() when no step is supplied.
    DEFAULT_STEP: float = 0.05

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        event_id: str,
        asset_id: str,
        initial_level: float = 0.0,
        default_step: float = DEFAULT_STEP,
    ) -> None:
        """
        Parameters
        ----------
        event_id:
            Non-empty, caller-supplied identifier. Unique within a
            given EventManager or Leaks-style collection.
        asset_id:
            Non-empty target asset ID. Must refer to a Pipeline,
            Pump Station, or Valve when validate() runs.
        initial_level:
            Starting deterioration level, in [0.0, 1.0].
        default_step:
            Step size used by advance() when no step is supplied.
            Must be in (0.0, 1.0].
        """

        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string.")

        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("asset_id must be a non-empty string.")

        if not isinstance(initial_level, (int, float)):
            raise ValueError("initial_level must be a number.")

        if initial_level < 0.0 or initial_level > 1.0:
            raise ValueError(
                "initial_level must be within the range [0.0, 1.0]."
            )

        if not isinstance(default_step, (int, float)):
            raise ValueError("default_step must be a number.")

        if default_step <= 0.0 or default_step > 1.0:
            raise ValueError("default_step must be within the range (0.0, 1.0].")

        self.event_id: str = event_id.strip()
        self.asset_id: str = asset_id.strip()
        self.deterioration_level: float = float(initial_level)
        self.default_step: float = float(default_step)

        self.active: bool = False
        self.start_time: Optional[str] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        """Mark this event active and record the first start time."""
        self.active = True
        if self.start_time is None:
            self.start_time = datetime.now().isoformat()

    def deactivate(self) -> None:
        """Mark this event inactive. Level is preserved."""
        self.active = False

    def reset(self) -> None:
        """
        Return the event to its initial state:

        - deterioration_level = 0.0
        - active = False
        - start_time = None
        """
        self.deterioration_level = 0.0
        self.active = False
        self.start_time = None

    # ------------------------------------------------------------------
    # Progression
    # ------------------------------------------------------------------

    def advance(self, step: Optional[float] = None) -> float:
        """
        Increase deterioration level by 'step' (clamped to [0.0, 1.0]).

        If step is None, uses self.default_step.

        Returns the new deterioration level.
        """
        if step is None:
            step = self.default_step

        if not isinstance(step, (int, float)):
            raise ValueError("step must be a number.")

        if step < 0.0:
            raise ValueError("step must not be negative.")

        new_level = self.deterioration_level + float(step)

        if new_level < 0.0:
            new_level = 0.0
        if new_level > 1.0:
            new_level = 1.0

        self.deterioration_level = new_level
        return new_level

    def set_level(self, level: float) -> float:
        """
        Directly set the deterioration level, clamped to [0.0, 1.0].

        Intended for tests, demos, and viva scenarios.
        Returns the stored level.
        """
        if not isinstance(level, (int, float)):
            raise ValueError("level must be a number.")

        if level < 0.0:
            level = 0.0
        if level > 1.0:
            level = 1.0

        self.deterioration_level = float(level)
        return self.deterioration_level

    # ------------------------------------------------------------------
    # Validation hook used by EventManager
    # ------------------------------------------------------------------

    def validate(self, assets_by_id: Dict[str, Any]) -> None:
        """
        Called by EventManager._validate_target().

        Checks the target asset exists and is a supported type for
        deterioration. Raises ValueError otherwise.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"DeteriorationEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type not in self.SUPPORTED_ASSET_TYPES:
            supported = ", ".join(t.value for t in self.SUPPORTED_ASSET_TYPES)
            raise ValueError(
                f"DeteriorationEvent does not support asset type "
                f"{actual_type}. Supported: {supported}."
            )

    # ------------------------------------------------------------------
    # Effect application
    # ------------------------------------------------------------------

    def apply(
        self,
        readings: List[Dict[str, Any]],
        assets_by_id: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Apply the deterioration effect to the given readings.

        Returns a NEW list. The caller's list is not modified in place.

        Contract
        --------
        apply() is a pure function of (input readings, current level).
        It does not compound when called repeatedly on the SAME readings
        only because EventManager.apply_events() calls it once per event
        per invocation. The intended usage is:

            readings = generate_all_readings()    # fresh normal readings
            readings = manager.apply_events(readings)

        The caller is responsible for not passing already-modified
        readings back into the same apply() chain twice.

        Effects per supported parameter (see class docstring for the
        exact multipliers):

            Pressure           -> decreases
            Flow Rate          -> decreases
            Temperature        -> increases
            Vibration          -> increases
            Power Consumption  -> increases
            Valve Position     -> decreases

        Non-numeric values are passed through. Unrelated parameters are
        passed through. Readings for other assets are passed through.
        """

        if not isinstance(readings, list):
            raise ValueError("readings must be a list of dictionaries.")

        # Look up the target asset so we know which parameters apply.
        asset = assets_by_id.get(self.asset_id) if isinstance(assets_by_id, dict) else None
        asset_type = getattr(asset, "asset_type", None) if asset is not None else None

        affected_params = self.AFFECTED_PARAMETERS.get(asset_type, set())
        if not affected_params:
            # Either asset is missing or its type is unsupported.
            # validate() would raise earlier in normal EventManager use.
            # Here we simply pass everything through.
            return list(readings)

        level = self.deterioration_level
        result: List[Dict[str, Any]] = []

        for reading in readings:

            # Pass through anything that is not our target asset.
            if reading.get("asset_id") != self.asset_id:
                result.append(reading)
                continue

            parameter = reading.get("parameter")

            # Pass through parameters we do not affect.
            if parameter not in affected_params:
                result.append(reading)
                continue

            # Only numeric values can be scaled.
            current_value = reading.get("value")
            if not isinstance(current_value, (int, float)):
                result.append(reading)
                continue

            new_value = self._scale_value(parameter, float(current_value), level)

            # Safety clamp: never produce impossible negatives.
            if new_value < 0.0:
                new_value = 0.0

            # Build a new dict so the original reading is untouched.
            new_reading = dict(reading)
            new_reading["value"] = round(new_value, 2)
            result.append(new_reading)

        return result

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """
        Simple, JSON-friendly status snapshot.

        Contains only event metadata. No analytics, no scoring.
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "asset_id": self.asset_id,
            "deterioration_level": round(self.deterioration_level, 4),
            "active": self.active,
            "start_time": self.start_time,
        }

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"DeteriorationEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"level={self.deterioration_level:.2f}, "
            f"active={self.active})"
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _scale_value(self, parameter: str, value: float, level: float) -> float:
        """
        Return the deteriorated value for one parameter.

        All multipliers are linear in 'level'. See class constants
        for the maximum fractional change at level = 1.0.
        """

        if parameter == "Pressure":
            factor = 1.0 - self.MAX_PRESSURE_REDUCTION * level
            return value * factor

        if parameter == "Flow Rate":
            factor = 1.0 - self.MAX_FLOW_REDUCTION * level
            return value * factor

        if parameter == "Temperature":
            factor = 1.0 + self.MAX_TEMPERATURE_INCREASE * level
            return value * factor

        if parameter == "Vibration":
            factor = 1.0 + self.MAX_VIBRATION_INCREASE * level
            return value * factor

        if parameter == "Power Consumption":
            factor = 1.0 + self.MAX_POWER_INCREASE * level
            return value * factor

        if parameter == "Valve Position":
            factor = 1.0 - self.MAX_VALVE_POSITION_REDUCTION * level
            return value * factor

        # Any other parameter is not affected.
        return value