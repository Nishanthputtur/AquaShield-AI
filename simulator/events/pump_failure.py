"""
pump_failure.py - Pump Station failure event for AquaShield AI.

Purpose
-------
Represents a controlled failure of one Pump Station. It modifies the
six readings attached to that pump so the station looks distressed
and eventually failed:

    Pressure             decreases
    Flow Rate            decreases
    Temperature          increases
    Vibration            increases
    Power Consumption    increases
    Equipment Status     moves to "OFF" above a severity threshold

Design
------
- One event targets one Pump Station. No other asset type is accepted.
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
are changed. Equipment Status is replaced with a valid status string.
Everything else is passed through unchanged.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from simulator.city.assets import AssetType


class PumpFailureEvent:
    """
    A single Pump Station failure event.

    Effects at severity = 1.0:

        Pressure           decreases by up to MAX_PRESSURE_REDUCTION (60%)
        Flow Rate          decreases by up to MAX_FLOW_REDUCTION (70%)
        Temperature        increases by up to MAX_TEMPERATURE_INCREASE (50%)
        Vibration          increases by up to MAX_VIBRATION_INCREASE (150%)
        Power Consumption  increases by up to MAX_POWER_INCREASE (40%)
        Equipment Status   set to "OFF" when severity >= FAILURE_THRESHOLD

    All numeric effects scale linearly:

        decrease factor = 1 - severity * MAX_*_REDUCTION
        increase factor = 1 + severity * MAX_*_INCREASE

    Values are clamped to >= 0.
    """

    # ------------------------------------------------------------------
    # Class-level configuration
    # ------------------------------------------------------------------

    event_type: str = "pump_failure"

    # Only Pump Stations are valid targets for this event.
    expected_asset_type: AssetType = AssetType.PUMP_STATION

    # Parameters this event is allowed to modify.
    AFFECTED_PARAMETERS = (
        "Pressure",
        "Flow Rate",
        "Temperature",
        "Vibration",
        "Power Consumption",
        "Equipment Status",
    )

    # Maximum fractional changes at severity = 1.0.
    MAX_PRESSURE_REDUCTION: float = 0.60
    MAX_FLOW_REDUCTION: float = 0.70
    MAX_TEMPERATURE_INCREASE: float = 0.50
    MAX_VIBRATION_INCREASE: float = 1.50
    MAX_POWER_INCREASE: float = 0.40

    # At or above this severity the pump is considered fully failed
    # and Equipment Status becomes "OFF".
    FAILURE_THRESHOLD: float = 0.5

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
            Non-empty target asset ID. Must refer to a Pump Station
            when validate() runs.
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

        Checks the target asset exists and is a Pump Station.
        Raises ValueError otherwise.
        """

        if not isinstance(assets_by_id, dict):
            raise ValueError("assets_by_id must be a dictionary.")

        if self.asset_id not in assets_by_id:
            raise ValueError(
                f"PumpFailureEvent target asset not found: {self.asset_id}"
            )

        asset = assets_by_id[self.asset_id]
        actual_type = getattr(asset, "asset_type", None)

        if actual_type != self.expected_asset_type:
            raise ValueError(
                f"PumpFailureEvent only supports "
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
        Apply the pump failure effect to the given readings.

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
        pressure_factor = 1.0 - self.severity * self.MAX_PRESSURE_REDUCTION
        flow_factor = 1.0 - self.severity * self.MAX_FLOW_REDUCTION
        temp_factor = 1.0 + self.severity * self.MAX_TEMPERATURE_INCREASE
        vib_factor = 1.0 + self.severity * self.MAX_VIBRATION_INCREASE
        power_factor = 1.0 + self.severity * self.MAX_POWER_INCREASE

        status_is_failed = self.severity >= self.FAILURE_THRESHOLD

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

            # Special case: Equipment Status is a string.
            if parameter == "Equipment Status":
                if status_is_failed:
                    new_reading = dict(reading)
                    new_reading["value"] = "OFF"
                    result.append(new_reading)
                else:
                    result.append(reading)
                continue

            # All remaining affected parameters are numeric.
            current_value = reading.get("value")
            if not isinstance(current_value, (int, float)):
                result.append(reading)
                continue

            if parameter == "Pressure":
                new_value = current_value * pressure_factor
            elif parameter == "Flow Rate":
                new_value = current_value * flow_factor
            elif parameter == "Temperature":
                new_value = current_value * temp_factor
            elif parameter == "Vibration":
                new_value = current_value * vib_factor
            elif parameter == "Power Consumption":
                new_value = current_value * power_factor
            else:
                result.append(reading)
                continue

            if new_value < 0.0:
                new_value = 0.0

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
            f"PumpFailureEvent(event_id={self.event_id!r}, "
            f"asset_id={self.asset_id!r}, "
            f"severity={self.severity}, "
            f"active={self.active})"
        )