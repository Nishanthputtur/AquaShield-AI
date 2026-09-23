"""
leak.py - Individual leak event for AquaShield AI.

A LeakEvent represents one leakage condition on one target asset.

Design:

- Target asset type: Pipeline only. The project does not explicitly
  support leakage on other asset types, so no other target is allowed.
- Affected parameters: "Flow Rate" and "Pressure".
  A leak reduces both. Higher severity produces a stronger reduction.
- No network propagation. Only the target asset's readings are changed.
- No analytics, no scoring, no database access.

Compatible with simulator/events/event_manager.py:

- Attributes : event_id, asset_id, active, severity, expected_asset_type
- Methods    : activate(), deactivate(), apply(readings, assets_by_id),
               validate(assets_by_id), to_dict()

The reading schema is preserved exactly:

    {
        "sensor_id": str,
        "asset_id": str,
        "parameter": str,
        "value": float | str,
        "unit": str,
        "timestamp": str
    }

No event metadata is added to readings.
"""

from datetime import datetime
from typing import Any, Dict, List

from simulator.city.assets import AssetType


class LeakEvent:
    """
    One leak event targeting one Pipeline asset.

    Effects at full severity (severity = 1.0):

    - Flow Rate is reduced by up to MAX_FLOW_REDUCTION (50%).
    - Pressure is reduced by up to MAX_PRESSURE_REDUCTION (40%).

    Effects scale linearly with severity:

        factor = 1.0 - severity * MAX_REDUCTION

    So severity = 0.0 leaves readings unchanged, severity = 1.0
    produces the maximum configured reduction.

    Values are clamped to >= 0.
    """

    # ------------------------------------------------------------------
    # Class-level constants and identifiers
    # ------------------------------------------------------------------

    event_type: str = "leak"

    # Only Pipelines are valid leak targets in the current project.
    expected_asset_type: AssetType = AssetType.PIPELINE

    # Maximum reductions at severity = 1.0.
    MAX_FLOW_REDUCTION: float = 0.5
    MAX_PRESSURE_REDUCTION: float = 0.4

    # Parameters this event is allowed to modify.
    AFFECTED_PARAMETERS = ("Flow Rate", "Pressure")

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
            Non-empty, caller-supplied identifier. Must be unique within
            an EventManager instance.
        asset_id:
            Non-empty asset ID. Must refer to a Pipeline when validated.
        severity:
            Float in the range [0.0, 1.0]. 0.0 means no effect, 1.0 means
            the maximum configured reduction.
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
        self.start_time: str = None  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def activate(self) -> None:
        """Mark this event as active and record the start time once."""
        self.active = True
        if self.start_time is None:
            self.start_time = datetime.now().isoformat()

    def deactivate(self) -> None:
        """Mark this event as inactive."""
        self.active = False

    # ------------------------------------------------------------------
    # Validation hook used by EventManager
    # ------------------------------------------------------------------

    def validate(self, assets_by_id: Dict[str, Any]) -> None:
        """
        Called by EventManager._validate_target().

        Ensures the target asset exists and is a Pipeline. Raises
        ValueError for unsupported or unknown targets.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"LeakEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type != self.expected_asset_type:
            raise ValueError(
                f"LeakEvent only supports "
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
        Apply the leak effect to the given readings.

        Returns a NEW list. The caller's list is not modified in place.
        For each reading:

        - If asset_id does not match, the reading is passed through.
        - If parameter is not affected, the reading is passed through.
        - If parameter is "Flow Rate" or "Pressure", a new reading dict
          is produced with a reduced value. All other fields are copied
          unchanged.

        The reading schema is preserved exactly. No event metadata is
        added to readings.

        This method is a pure function of the readings it receives.
        It does not track how many times it has been called and does
        not compound by itself. EventManager is responsible for calling
        it once per event per apply_events() call.
        """

        if not isinstance(readings, list):
            raise ValueError("readings must be a list of dictionaries.")

        # Precompute reduction factors from severity.
        flow_factor = 1.0 - self.severity * self.MAX_FLOW_REDUCTION
        pressure_factor = 1.0 - self.severity * self.MAX_PRESSURE_REDUCTION

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

            if parameter == "Flow Rate":
                new_value = current_value * flow_factor
            else:  # parameter == "Pressure"
                new_value = current_value * pressure_factor

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
        Return a simple, JSON-friendly status snapshot.

        Used by EventManager.get_event_status() for future backend/UI
        integration. No analytics results are included here.
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
            f"LeakEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"severity={self.severity}, "
            f"active={self.active})"
        )