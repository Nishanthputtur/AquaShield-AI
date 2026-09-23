"""
water_quality.py - Water-quality abnormality event for AquaShield AI.

Purpose
-------
Represents an abnormal water-quality condition on one target asset
(Reservoir or Treatment Facility).

Effects at severity = 1.0:

    pH                 decreases by up to MAX_PH_REDUCTION (30%)
    Turbidity          increases by up to MAX_TURBIDITY_INCREASE (300%)
    Water Temperature  increases by up to MAX_WATER_TEMP_INCREASE (60%)

Water Level is NOT affected. It is an operational/quantity parameter,
not a quality parameter, and is intentionally left unchanged.

Design
------
- One event targets one Reservoir or one Treatment Facility.
- Severity in [0.0, 1.0]. Effects scale linearly.
- Local to the target asset. No upstream/downstream propagation.
- apply() is a pure function of (input readings, severity). It does
  not compound by itself; EventManager calls each active event once
  per apply_events() invocation, and the caller passes fresh normal
  readings each simulation step.

Compatible with simulator/events/event_manager.py:

- Attributes : event_id, asset_id, active, severity
- Methods    : activate(), deactivate(), apply(readings, assets_by_id),
               validate(assets_by_id), to_dict()

Note: expected_asset_type is intentionally NOT declared as a class
attribute. Two asset types are valid, and EventManager's
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


class WaterQualityEvent:
    """
    A single water-quality abnormality event.

    Supported asset types:

        Reservoir
        Treatment Facility

    Affected parameters (for both supported types):

        pH
        Turbidity
        Water Temperature

    Effects at severity = 1.0:

        pH                 decreases by up to MAX_PH_REDUCTION
        Turbidity          increases by up to MAX_TURBIDITY_INCREASE
        Water Temperature  increases by up to MAX_WATER_TEMP_INCREASE

    All effects scale linearly with severity:

        decrease factor = 1 - severity * MAX_*_REDUCTION
        increase factor = 1 + severity * MAX_*_INCREASE

    pH is clamped to [0.0, 14.0].
    Turbidity and Water Temperature are clamped to >= 0.0.

    Water Level is intentionally left unchanged.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    event_type: str = "water_quality"

    # Only these asset types carry water-quality sensors.
    SUPPORTED_ASSET_TYPES = (
        AssetType.RESERVOIR,
        AssetType.TREATMENT_FACILITY,
    )

    # Parameters this event is allowed to modify on the target asset.
    # Water Level is intentionally excluded.
    AFFECTED_PARAMETERS = ("pH", "Turbidity", "Water Temperature")

    # Maximum fractional changes at severity = 1.0.
    MAX_PH_REDUCTION: float = 0.30
    MAX_TURBIDITY_INCREASE: float = 3.00
    MAX_WATER_TEMP_INCREASE: float = 0.60

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(
        self,
        event_id: str,
        asset_id: str,
        severity: float = 0.6,
    ) -> None:
        """
        Parameters
        ----------
        event_id:
            Non-empty, caller-supplied identifier. Unique within a
            given EventManager instance.
        asset_id:
            Non-empty target asset ID. Must refer to a Reservoir or a
            Treatment Facility when validate() runs.
        severity:
            Float in [0.0, 1.0]. 0.0 means no effect, 1.0 means the
            maximum configured abnormality effect.
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

        Checks the target asset exists and is a supported type for
        water-quality events. Raises ValueError otherwise.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"WaterQualityEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type not in self.SUPPORTED_ASSET_TYPES:
            supported = ", ".join(t.value for t in self.SUPPORTED_ASSET_TYPES)
            raise ValueError(
                f"WaterQualityEvent does not support asset type "
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
        Apply the water-quality effect to the given readings.

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
        ph_factor = 1.0 - self.severity * self.MAX_PH_REDUCTION
        turbidity_factor = 1.0 + self.severity * self.MAX_TURBIDITY_INCREASE
        water_temp_factor = 1.0 + self.severity * self.MAX_WATER_TEMP_INCREASE

        result: List[Dict[str, Any]] = []

        for reading in readings:

            # Pass through anything that is not our target asset.
            if reading.get("asset_id") != self.asset_id:
                result.append(reading)
                continue

            parameter = reading.get("parameter")

            # Pass through unaffected parameters on the target asset.
            # This also passes Water Level through unchanged.
            if parameter not in self.AFFECTED_PARAMETERS:
                result.append(reading)
                continue

            # Only numeric values can be scaled.
            current_value = reading.get("value")
            if not isinstance(current_value, (int, float)):
                result.append(reading)
                continue

            if parameter == "pH":
                new_value = current_value * ph_factor
                # pH is bounded.
                if new_value < 0.0:
                    new_value = 0.0
                if new_value > 14.0:
                    new_value = 14.0
            elif parameter == "Turbidity":
                new_value = current_value * turbidity_factor
                if new_value < 0.0:
                    new_value = 0.0
            elif parameter == "Water Temperature":
                new_value = current_value * water_temp_factor
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
            f"WaterQualityEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"severity={self.severity}, "
            f"active={self.active})"
        )