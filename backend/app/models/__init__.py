"""ORM models for AquaShield AI.

Importing this module registers all 18 tables with `Base.metadata`.

Import order matters for FK resolution:
    users, cities, zones  -> no dependencies between them
    assets                -> depends on zones; self-FK to assets
    asset subtypes        -> depend on assets
    sensors               -> depend on assets
    sensor_readings       -> depend on sensors
    anomalies             -> depend on assets and sensor_readings
    asset_health_scores   -> depend on assets
    risk_scores           -> depend on assets
    inspections           -> depend on assets and users
    maintenance_records   -> depend on assets and users
    complaints            -> depend on zones
    notifications         -> depend on complaints
"""

from backend.app.models.user import User
from backend.app.models.city import City
from backend.app.models.zone import Zone
from backend.app.models.asset import (
    Asset,
    TreatmentFacility,
    Reservoir,
    PumpStation,
    Pipeline,
    Valve,
)
from backend.app.models.sensor import (
    Sensor,
    SensorReading,
    Anomaly,
)
from backend.app.models.maintenance import (
    AssetHealthScore,
    RiskScore,
    Inspection,
    MaintenanceRecord,
)
from backend.app.models.complaint import (
    Complaint,
    Notification,
)


__all__ = [
    "User",
    "City",
    "Zone",
    "Asset",
    "TreatmentFacility",
    "Reservoir",
    "PumpStation",
    "Pipeline",
    "Valve",
    "Sensor",
    "SensorReading",
    "Anomaly",
    "AssetHealthScore",
    "RiskScore",
    "Inspection",
    "MaintenanceRecord",
    "Complaint",
    "Notification",
]