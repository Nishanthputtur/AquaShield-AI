from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from backend.app.models import (
    Asset,
    Anomaly,
    AssetHealthScore,
    RiskScore,
    Sensor,
    SensorReading,
    MaintenanceRecord,
)


PRESSURE_RANGES = {
    "Pipeline": (40.0, 60.0),
    "Valve": (40.0, 60.0),
    "PumpStation": (60.0, 80.0),
}

CRITICALITY = {
    "TreatmentFacility": 1.5,
    "PumpStation": 1.3,
    "Reservoir": 1.2,
    "Pipeline": 1.0,
    "Valve": 0.8,
}

ANOMALY_DEDUPLICATION_MINUTES = 5
MAINTENANCE_LOOKBACK_DAYS = 7
MAINTENANCE_QUEUE_LIMIT = 10

RESOLVED_STATUSES = {
    "resolved",
    "closed",
    "completed",
}


def _get_sensor_parameter(sensor: Sensor) -> str | None:
    """Resolve the actual simulator parameter represented by a DB sensor."""

    sensor_type = (sensor.sensor_type or "").strip()

    standard_parameters = {
        "Flow": "Flow Rate",
        "Pressure": "Pressure",
        "Level": "Water Level",
        "Water Temperature": "Water Temperature",
        "pH": "pH",
        "Turbidity": "Turbidity",
    }

    if sensor_type in standard_parameters:
        return standard_parameters[sensor_type]

    if sensor_type != "Equipment Condition":
        return None

    name = (sensor.sensor_name or "").upper().replace("_", "-")

    if "EQUIPMENT-STATUS" in name:
        return "Equipment Status"
    if "VIBRATION" in name:
        return "Vibration"
    if "POWER" in name:
        return "Power Consumption"
    if "POSITION" in name:
        return "Valve Position"
    if "TEMPERATURE" in name:
        return "Temperature"

    return None


def _parse_reading(reading: SensorReading):
    """
    Return (numeric_value, text_value).

    Numeric equipment values are stored in reading_value_text under
    the approved Decision 4 database design.
    """

    if reading.reading_value_numeric is not None:
        return float(reading.reading_value_numeric), None

    raw_value = reading.reading_value_text

    if raw_value is None:
        return None, None

    try:
        return float(raw_value), None
    except (TypeError, ValueError):
        return None, str(raw_value).strip().upper()


def _get_latest_reading(
    db: Session,
    sensor_id: int,
) -> SensorReading | None:
    """Retrieve the latest reading for one sensor."""

    return (
        db.query(SensorReading)
        .filter(SensorReading.sensor_id == sensor_id)
        .order_by(
            SensorReading.timestamp.desc(),
            SensorReading.reading_id.desc(),
        )
        .first()
    )


def _is_unresolved(anomaly: Anomaly) -> bool:
    """Treat resolved, closed and completed anomalies as inactive."""

    status = (anomaly.status or "").strip().lower()
    return status not in RESOLVED_STATUSES


def _has_recent_unresolved_anomaly(
    db: Session,
    asset_id: int,
    anomaly_type: str,
    cutoff: datetime,
) -> bool:
    """Check the five-minute duplicate-prevention window."""

    existing = (
        db.query(Anomaly)
        .filter(
            Anomaly.asset_id == asset_id,
            Anomaly.anomaly_type == anomaly_type,
            Anomaly.detected_at >= cutoff,
        )
        .all()
    )

    return any(_is_unresolved(item) for item in existing)


def _reading_sort_key(reading: SensorReading) -> tuple[datetime, int]:
    """Order readings by timestamp, then reading ID."""

    return getattr(reading, "timestamp", datetime.min), reading.reading_id


def _detect_asset_anomalies(
    asset: Asset,
    readings: list[dict],
) -> list[dict]:
    """Evaluate the approved rule-based anomaly conditions."""

    detected = []

    latest_by_parameter = {}

    def add_anomaly(
        anomaly_type: str,
        reading: SensorReading,
        description: str,
    ):
        detected.append({
            "anomaly_type": anomaly_type,
            "sensor_reading_id": reading.reading_id,
            "description": description,
            "sort_key": _reading_sort_key(reading),
        })

    pressure_range = PRESSURE_RANGES.get(asset.asset_type)

    for entry in readings:
        parameter = entry["parameter"]
        reading = entry["reading"]
        numeric_value = entry["numeric_value"]
        text_value = entry["text_value"]

        current_entry = latest_by_parameter.get(parameter)
        if (
            current_entry is None
            or _reading_sort_key(entry["reading"])
            > _reading_sort_key(current_entry["reading"])
        ):
            latest_by_parameter[parameter] = entry

        if parameter == "Pressure" and numeric_value is not None:
            if pressure_range is not None:
                low, high = pressure_range

                if numeric_value < low:
                    add_anomaly(
                        "Low Pressure",
                        reading,
                        f"Pressure {numeric_value:.2f} PSI "
                        f"is below the lower limit of {low:.2f} PSI.",
                    )

                elif numeric_value > high:
                    add_anomaly(
                        "High Pressure",
                        reading,
                        f"Pressure {numeric_value:.2f} PSI "
                        f"exceeds the upper limit of {high:.2f} PSI.",
                    )

        elif parameter == "Flow Rate" and numeric_value is not None:
            if numeric_value < 80:
                add_anomaly(
                    "Low Flow",
                    reading,
                    f"Flow {numeric_value:.2f} L/min "
                    "is below the normal lower limit of 80 L/min.",
                )

        elif parameter == "Temperature" and numeric_value is not None:
            if numeric_value > 40:
                add_anomaly(
                    "Overheating",
                    reading,
                    f"Equipment temperature {numeric_value:.2f} °C "
                    "exceeds the upper limit of 40 °C.",
                )

        elif parameter == "Vibration" and numeric_value is not None:
            if numeric_value > 5:
                add_anomaly(
                    "Excessive Vibration",
                    reading,
                    f"Vibration {numeric_value:.2f} mm/s "
                    "exceeds the upper limit of 5 mm/s.",
                )

        elif parameter == "Power Consumption" and numeric_value is not None:
            if numeric_value > 50:
                add_anomaly(
                    "Overpower",
                    reading,
                    f"Power consumption {numeric_value:.2f} kW "
                    "exceeds the upper limit of 50 kW.",
                )

        elif parameter == "Valve Position" and numeric_value is not None:
            if numeric_value < 20 or numeric_value > 80:
                add_anomaly(
                    "Abnormal Valve Position",
                    reading,
                    f"Valve position {numeric_value:.2f}% "
                    "is outside the normal range of 20% to 80%.",
                )

        elif parameter == "Equipment Status":
            pass

        elif parameter == "pH" and numeric_value is not None:
            if numeric_value < 6.5 or numeric_value > 8.5:
                add_anomaly(
                    "Abnormal pH",
                    reading,
                    f"pH value {numeric_value:.2f} "
                    "is outside the approved simulator range of 6.5 to 8.5.",
                )

        elif parameter == "Turbidity" and numeric_value is not None:
            if numeric_value > 5:
                add_anomaly(
                    "High Turbidity",
                    reading,
                    f"Turbidity {numeric_value:.2f} NTU "
                    "exceeds the simulator upper limit of 5 NTU.",
                )

        elif parameter == "Water Temperature" and numeric_value is not None:
            if numeric_value < 10 or numeric_value > 25:
                add_anomaly(
                    "Abnormal Water Temperature",
                    reading,
                    f"Water temperature {numeric_value:.2f} °C "
                    "is outside the simulator range of 10 °C to 25 °C.",
                )

        elif parameter == "Water Level" and numeric_value is not None:
            if numeric_value < 5 or numeric_value > 15:
                add_anomaly(
                    "Abnormal Reservoir Level",
                    reading,
                    f"Water level {numeric_value:.2f} ft "
                    "is outside the simulator range of 5 ft to 15 ft.",
                )

    pressure_entry = latest_by_parameter.get("Pressure")
    flow_entry = latest_by_parameter.get("Flow Rate")
    equipment_status_entry = latest_by_parameter.get("Equipment Status")

    # Possible leak: simultaneous low flow and low pressure.
    if flow_entry is not None and pressure_entry is not None:
        flow_value = flow_entry["numeric_value"]
        pressure_value = pressure_entry["numeric_value"]

        if (
            flow_value is not None
            and pressure_value is not None
            and flow_value < 80
            and pressure_value < 40
        ):
            add_anomaly(
                "Possible Leak",
                flow_entry["reading"],
                (
                    f"Possible leak indicated by simultaneous flow "
                    f"drop ({flow_value:.2f} L/min) and pressure "
                    f"drop ({pressure_value:.2f} PSI). "
                    f"Pressure reading ID: "
                    f"{pressure_entry['reading'].reading_id}."
                ),
            )

    # Equipment status OFF alone is not treated as a failure.
    if (
        equipment_status_entry is not None
        and equipment_status_entry["text_value"] == "OFF"
        and pressure_entry is not None
        and pressure_entry["numeric_value"] is not None
        and pressure_range is not None
    ):
        pressure_value = pressure_entry["numeric_value"]
        low, high = pressure_range

        if pressure_value < low or pressure_value > high:
            status_reading = equipment_status_entry["reading"]

            add_anomaly(
                "Possible Equipment Failure",
                status_reading,
                (
                    "Equipment status is OFF while pressure is "
                    f"abnormal ({pressure_value:.2f} PSI; "
                    f"expected {low:.2f} to {high:.2f} PSI)."
                ),
            )

    return detected


def _count_active_anomalies(db: Session, asset_id: int) -> int:
    """Count unresolved anomaly records for one asset."""

    anomalies = (
        db.query(Anomaly)
        .filter(Anomaly.asset_id == asset_id)
        .all()
    )

    return sum(1 for item in anomalies if _is_unresolved(item))


def _count_recent_maintenance(
    db: Session,
    asset_id: int,
    cutoff: datetime,
    now: datetime,
) -> int:
    """Count maintenance records dated within the preceding seven days."""

    return (
        db.query(MaintenanceRecord)
        .filter(
            MaintenanceRecord.asset_id == asset_id,
            MaintenanceRecord.maintenance_date >= cutoff,
            MaintenanceRecord.maintenance_date <= now,
        )
        .count()
    )


def run_analytics_for_all(db: Session) -> dict:
    """
    Process all assets and calculate anomalies, AHS, RS and
    internal maintenance decision outputs.

    Predictive maintenance forecasting is not implemented because
    no forecasting rule has been approved.
    """

    now = datetime.now()
    deduplication_cutoff = now - timedelta(
        minutes=ANOMALY_DEDUPLICATION_MINUTES
    )
    maintenance_cutoff = now - timedelta(
        days=MAINTENANCE_LOOKBACK_DAYS
    )

    assets = db.query(Asset).order_by(Asset.asset_id.asc()).all()

    total_anomalies = 0
    asset_decisions = []

    try:
        for asset in assets:
            asset_sensors = (
                db.query(Sensor)
                .filter(Sensor.asset_id == asset.asset_id)
                .all()
            )

            latest_readings = []

            # Retrieve one latest reading for every sensor.
            for sensor in asset_sensors:
                reading = _get_latest_reading(db, sensor.sensor_id)

                if reading is None:
                    continue

                parameter = _get_sensor_parameter(sensor)

                if parameter is None:
                    continue

                numeric_value, text_value = _parse_reading(reading)

                latest_readings.append({
                    "parameter": parameter,
                    "reading": reading,
                    "numeric_value": numeric_value,
                    "text_value": text_value,
                })

            candidates = _detect_asset_anomalies(
                asset,
                latest_readings,
            )

            selected_candidates = {}

            for candidate in candidates:
                anomaly_type = candidate["anomaly_type"]
                existing_candidate = selected_candidates.get(anomaly_type)

                # Preserve one anomaly per asset and type, associating it
                # with the newest qualifying reading deterministically.
                if (
                    existing_candidate is None
                    or candidate["sort_key"] > existing_candidate["sort_key"]
                ):
                    selected_candidates[anomaly_type] = candidate

            for anomaly_type in sorted(selected_candidates):
                candidate = selected_candidates[anomaly_type]

                if _has_recent_unresolved_anomaly(
                    db,
                    asset.asset_id,
                    anomaly_type,
                    deduplication_cutoff,
                ):
                    continue

                db.add(Anomaly(
                    asset_id=asset.asset_id,
                    sensor_reading_id=candidate["sensor_reading_id"],
                    anomaly_type=anomaly_type,
                    description=candidate["description"],
                    detected_at=now,
                    status="Active",
                ))

                total_anomalies += 1

            # Make newly added anomalies visible to the score query.
            db.flush()

            active_anomaly_count = _count_active_anomalies(
                db,
                asset.asset_id,
            )

            maintenance_count = _count_recent_maintenance(
                db,
                asset.asset_id,
                maintenance_cutoff,
                now,
            )

            # C1: Asset Health Score.
            ahs_score = max(
                0.0,
                min(
                    100.0,
                    100.0
                    - (active_anomaly_count * 10)
                    - (maintenance_count * 2),
                ),
            )

            # C2: Risk Score.
            criticality = CRITICALITY[asset.asset_type]

            rs_score = min(
                100.0,
                max(0.0, (100.0 - ahs_score) * criticality),
            )

            db.add(AssetHealthScore(
                asset_id=asset.asset_id,
                score=round(ahs_score, 2),
                assessment_timestamp=now,
                explanation=(
                    f"AHS = 100 - "
                    f"({active_anomaly_count} active anomalies x 10) - "
                    f"({maintenance_count} maintenance records in "
                    f"the last 7 days x 2). "
                    f"Final score: {ahs_score:.2f}."
                ),
            ))

            db.add(RiskScore(
                asset_id=asset.asset_id,
                score=round(rs_score, 2),
                assessment_timestamp=now,
                explanation=(
                    f"RS = (100 - {ahs_score:.2f}) x "
                    f"{criticality:.2f} criticality. "
                    f"Final score: {rs_score:.2f}."
                ),
            ))

            # C3: Maintenance Priority.
            priority_score = (
                rs_score
                + (criticality * 10)
                + (active_anomaly_count * 5)
            )

            #C4: Explainable Recommendation.
            if rs_score > 75:
                recommended_action = "Immediate inspection"
            elif rs_score > 50:
                recommended_action = "Schedule maintenance"
            else:
                recommended_action = "Monitor"

            recommendation = (
                f"Asset {asset.asset_id} ({asset.asset_type}) "
                f"has AHS={ahs_score:.2f} and RS={rs_score:.2f}. "
                f"{active_anomaly_count} active anomalies detected. "
                f"Recommended: {recommended_action}"
            )

            asset_decisions.append({
                "asset_id": asset.asset_id,
                "asset_type": asset.asset_type,
                "ahs": round(ahs_score, 2),
                "rs": round(rs_score, 2),
                "anomaly_count": active_anomaly_count,
                "maintenance_priority": round(priority_score, 2),
                "recommendation": recommendation,
            })

        db.commit()

    except Exception:
        db.rollback()
        raise

    asset_decisions.sort(
        key=lambda item: (
            -item["maintenance_priority"],
            item["asset_id"],
        )
    )

    maintenance_queue = asset_decisions[:MAINTENANCE_QUEUE_LIMIT]

    return {
        "total_anomalies": total_anomalies,
        "assets_processed": len(assets),
        "asset_decisions": asset_decisions,
        "maintenance_queue": maintenance_queue,
    }
