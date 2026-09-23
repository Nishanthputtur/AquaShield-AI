"""
pressure_drop.py - Local pressure-drop event for AquaShield AI.

Purpose
-------
Represents a local abnormal pressure loss on one target asset.

Unlike DeteriorationEvent (gradual), this event is a sudden,
sustained pressure anomaly. Unlike LeakEvent (which focuses on flow
loss with pressure as a side effect), PressureDropEvent's primary
signature is the pressure reduction itself.

Design
------
- One event targets one asset.
- Supported asset types: PIPELINE, PUMP_STATION, VALVE.
  These are the asset types that carry Pressure sensors in the
  current sensor layer.
- Severity is a normalized value in [0.0, 1.0].
- Primary effect: Pressure decreases.
- Secondary effect: Flow Rate decreases by a smaller factor.
- Local to the target asset. No upstream/downstream propagation.
- apply() is a pure function of (input readings, severity).
  It does not compound by itself. The caller passes fresh normal
  readings to EventManager each simulation step.

Compatible with simulator/events/event_manager.py:

- Attributes : event_id, asset_id, active, severity
- Methods    : activate(), deactivate(), apply(readings, assets_by_id),
               validate(assets_by_id), to_dict()

Note: expected_asset_type is intentionally NOT declared as a class
attribute. Three asset types are valid, and EventManager's
_validate_target only checks a single expected type. Type validation
is done inside validate().

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


class PressureDropEvent:
    """
    A single local pressure-drop event on one target asset.

    Primary effect (severity = 1.0):
        Pressure  decreases by up to MAX_PRESSURE_REDUCTION (40%).

    Secondary effect (severity = 1.0):
        Flow Rate decreases by up to MAX_FLOW_REDUCTION (20%).

    Effects scale linearly with severity:

        factor = 1 - severity * MAX_REDUCTION

    So severity = 0.0 leaves readings unchanged, severity = 1.0
    produces the maximum configured reduction. Values are clamped
    to >= 0.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    event_type: str = "pressure_drop"

    # Only these asset types carry Pressure sensors in the current
    # sensor layer. Do not add other types here without extending the
    # sensor layer first.
    SUPPORTED_ASSET_TYPES = (
        AssetType.PIPELINE,
        AssetType.PUMP_STATION,
        AssetType.VALVE,
    )

    # Parameters this event is allowed to modify on the target asset.
    AFFECTED_PARAMETERS = ("Pressure", "Flow Rate")

    # Maximum reductions at severity = 1.0.
    MAX_PRESSURE_REDUCTION: float = 0.40
    MAX_FLOW_REDUCTION: float = 0.20

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        event_id: str,
        asset_id: str,
        severity: float = 0.5,
    ) -> None:
        """
        Parameters
        ----------
        event_id:
            Non-empty, caller-supplied identifier. Unique within a
            given EventManager instance.
        asset_id:
            Non-empty target asset ID. Must refer to a Pipeline,
            Pump Station, or Valve when validate() runs.
        severity:
            Float in [0.0, 1.0]. 0.0 means no effect, 1.0 means the
            maximum configured reduction.
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

        Checks the target asset exists and is a supported type.
        Raises ValueError otherwise.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"PressureDropEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type not in self.SUPPORTED_ASSET_TYPES:
            supported = ", ".join(t.value for t in self.SUPPORTED_ASSET_TYPES)
            raise ValueError(
                f"PressureDropEvent does not support asset type "
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
        Apply the pressure-drop effect to the given readings.

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

        # Precompute reduction factors from severity.
        pressure_factor = 1.0 - self.severity * self.MAX_PRESSURE_REDUCTION
        flow_factor = 1.0 - self.severity * self.MAX_FLOW_REDUCTION

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

            if parameter == "Pressure":
                new_value = current_value * pressure_factor
            else:  # parameter == "Flow Rate"
                new_value = current_value * flow_factor

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
            "severity": self.severity,
            "active": self.active,
            "start_time": self.start_time,
        }

    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"PressureDropEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"severity={self.severity}, "
            f"active={self.active})"
        )