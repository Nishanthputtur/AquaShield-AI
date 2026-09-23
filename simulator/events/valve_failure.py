"""
valve_failure.py - Valve malfunction event for AquaShield AI.

Purpose
-------
Represents a controlled malfunction of one Valve. It modifies the
three readings attached to that valve so the valve looks stuck,
restricted, or otherwise abnormal:

    Valve Position   decreases (valve drifts toward closed)
    Flow Rate        decreases (restricted flow through the valve)
    Pressure         increases (back pressure at the restricted valve)

Design
------
- One event targets one Valve. No other asset type is accepted.
- Severity in [0.0, 1.0]. Effects scale linearly.
- Local to the target asset. No upstream/downstream propagation.
- apply() is a pure function of (input readings, severity). It does
  not compound by itself; EventManager calls each active event once
  per apply_events() invocation, and the caller passes fresh normal
  readings each simulation step.

Compatible with simulator/events/event_manager.py:

- Attributes : event_id, asset_id, active, severity, expected_asset_type
- Methods    : activate(), deactivate(), apply(readings, assets_by_id),
               validate(assets_by_id), to_dict()

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


class ValveFailureEvent:
    """
    A single Valve malfunction event.

    Effects at severity = 1.0:

        Valve Position  decreases by up to MAX_VALVE_POSITION_REDUCTION (80%)
        Flow Rate       decreases by up to MAX_FLOW_REDUCTION (70%)
        Pressure        increases by up to MAX_PRESSURE_INCREASE (40%)

    Numeric effects scale linearly:

        decrease factor = 1 - severity * MAX_*_REDUCTION
        increase factor = 1 + severity * MAX_*_INCREASE

    Valve Position is clamped to [0.0, 100.0].
    Flow Rate and Pressure are clamped to >= 0.0.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    event_type: str = "valve_failure"

    # Only Valves are valid targets for this event.
    expected_asset_type: AssetType = AssetType.VALVE

    # Parameters this event is allowed to modify.
    AFFECTED_PARAMETERS = ("Valve Position", "Flow Rate", "Pressure")

    # Maximum fractional changes at severity = 1.0.
    MAX_VALVE_POSITION_REDUCTION: float = 0.80
    MAX_FLOW_REDUCTION: float = 0.70
    MAX_PRESSURE_INCREASE: float = 0.40

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        event_id: str,
        asset_id: str,
        severity: float = 0.7,
    ) -> None:
        """
        Parameters
        ----------
        event_id:
            Non-empty, caller-supplied identifier. Unique within a
            given EventManager instance.
        asset_id:
            Non-empty target asset ID. Must refer to a Valve when
            validate() runs.
        severity:
            Float in [0.0, 1.0]. 0.0 means no effect, 1.0 means the
            maximum configured failure effect.
        """

        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("event_id must be a non-empty string.")

        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError("asset_id must be a non-empty string.")

        if not isinstance(severity, (int, float)):
            raise ValueError("severity must be a number.")

        if severity < 0.0 or severity > 1.0:
            raise ValueError(
                "severity must be within the range [0.0, 1.0]."
            )

        self.event_id: str = event_id.strip()
        self.asset_id: str = asset_id.strip()
        self.severity: float = float(severity)

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
        """Mark this event inactive."""
        self.active = False

    # ------------------------------------------------------------------
    # Validation hook used by EventManager
    # ------------------------------------------------------------------

    def validate(self, assets_by_id: Dict[str, Any]) -> None:
        """
        Called by EventManager._validate_target().

        Checks the target asset exists and is a Valve.
        Raises ValueError otherwise.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"ValveFailureEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type != self.expected_asset_type:
            raise ValueError(
                f"ValveFailureEvent only supports "
                f"{self.expected_asset_type.value} targets, but "
                f"{self.asset_id} is {actual_type}."
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
        Apply the valve failure effect to the given readings.

        Returns a NEW list. The caller's list is not modified in place.

        Contract
        --------
        apply() is a pure function of (input readings, severity).
        It does not compound when called repeatedly on the same
        readings. The intended usage is:

            readings = generate_all_readings()    # fresh normal readings
            readings = manager.apply_events(readings)

        Only readings whose asset_id matches the target and whose
        parameter is one of AFFECTED_PARAMETERS are modified. All
        other readings are passed through unchanged. The reading
        schema is preserved exactly.
        """

        if not isinstance(readings, list):
            raise ValueError("readings must be a list of dictionaries.")

        # Precompute factors from severity.
        position_factor = 1.0 - self.severity * self.MAX_VALVE_POSITION_REDUCTION
        flow_factor = 1.0 - self.severity * self.MAX_FLOW_REDUCTION
        pressure_factor = 1.0 + self.severity * self.MAX_PRESSURE_INCREASE

        result: List[Dict[str, Any]] = []

        for reading in readings:

            # Pass through anything that is not our target asset.
            if reading.get("asset_id") != self.asset_id:
                result.append(reading)
                continue

            parameter = reading.get("parameter")

            # Pass through unaffected parameters on the target asset.
            if parameter not in self.AFFECTED_PARAMETERS:
                result.append(reading)
                continue

            # Only numeric values can be scaled.
            current_value = reading.get("value")
            if not isinstance(current_value, (int, float)):
                result.append(reading)
                continue

            if parameter == "Valve Position":
                new_value = current_value * position_factor
                # Valve Position is a percentage, clamp to [0, 100].
                if new_value < 0.0:
                    new_value = 0.0
                if new_value > 100.0:
                    new_value = 100.0
            elif parameter == "Flow Rate":
                new_value = current_value * flow_factor
                if new_value < 0.0:
                    new_value = 0.0
            elif parameter == "Pressure":
                new_value = current_value * pressure_factor
                if new_value < 0.0:
                    new_value = 0.0
            else:
                result.append(reading)
                continue

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
            "severity": self.severity,
            "active": self.active,
            "start_time": self.start_time,
        }

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"ValveFailureEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"severity={self.severity}, "
            f"active={self.active})"
        )