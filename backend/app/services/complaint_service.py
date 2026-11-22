"""
Public portal and complaint service for AquaShield AI.

Encapsulates data retrieval for public water supply status, pH water quality,
infrastructure, maintenance notices, public announcements, and complaint workflows.
"""

from datetime import datetime
import secrets
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.asset import Asset
from backend.app.models.city import City
from backend.app.models.complaint import Complaint, Notification
from backend.app.models.maintenance import MaintenanceRecord
from backend.app.models.sensor import Anomaly, Sensor, SensorReading
from backend.app.models.zone import Zone
from backend.app.services.asset_service import _display_name

# Approved project simulated pH reference range from simulator.sensors.water_quality
PH_THRESHOLD_MIN = 6.5
PH_THRESHOLD_MAX = 8.5

DEFAULT_PUBLIC_ANNOUNCEMENTS = (
    {
        "title": "Simulated Water Monitoring Platform",
        "message": (
            "AquaShield AI presents simulated water-system monitoring across "
            "four virtual cities and 16 zones."
        ),
        "notification_type": "System Advisory",
    },
    {
        "title": "Simulated pH Monitoring Reference Range",
        "message": (
            "The platform presents simulated pH monitoring against its "
            "configured project reference range of 6.5 to 8.5. This pH "
            "indicator alone does not assess overall drinking-water safety "
            "or regulatory compliance."
        ),
        "notification_type": "Water Quality",
    },
    {
        "title": "Routine Scheduled Infrastructure Inspection",
        "message": (
            "Field inspectors and maintenance officers conduct routine "
            "digital inspections of pipelines, valves, and pump stations."
        ),
        "notification_type": "Maintenance Notice",
    },
)


def ensure_seed_notifications(db: Session) -> None:
    """Seed initial simulated public announcements if the notifications table is empty."""
    if db.query(Notification).filter(Notification.complaint_id.is_(None)).count() == 0:
        initial_announcements = [
            Notification(
                complaint_id=None,
                title=announcement["title"],
                message=announcement["message"],
                notification_type=announcement["notification_type"],
                created_at=datetime.now(),
            )
            for announcement in DEFAULT_PUBLIC_ANNOUNCEMENTS
        ]
        db.add_all(initial_announcements)
        db.commit()


def get_public_notifications(db: Session) -> List[Notification]:
    """Retrieve public announcements (where complaint_id is NULL)."""
    ensure_seed_notifications(db)
    return (
        db.query(Notification)
        .filter(Notification.complaint_id.is_(None))
        .order_by(Notification.created_at.desc())
        .all()
    )


def get_public_cities(db: Session) -> List[Dict[str, Any]]:
    """Retrieve all virtual cities with nested zones."""
    cities = db.query(City).order_by(City.city_id.asc()).all()
    result = []
    for c in cities:
        zones = (
            db.query(Zone)
            .filter(Zone.city_id == c.city_id)
            .order_by(Zone.zone_id.asc())
            .all()
        )
        result.append({
            "city_id": c.city_id,
            "city_name": c.city_name,
            "description": c.description,
            "zones": [
                {
                    "zone_id": z.zone_id,
                    "name": z.zone_name,
                    "city_id": c.city_id,
                    "city_name": c.city_name,
                }
                for z in zones
            ],
        })
    return result


def get_public_zones(db: Session, city_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retrieve zones, optionally filtered by city_id, preserving backward compatibility."""
    query = (
        db.query(Zone, City)
        .join(City, Zone.city_id == City.city_id)
        .order_by(Zone.zone_id.asc())
    )
    if city_id is not None:
        query = query.filter(Zone.city_id == city_id)

    rows = query.all()
    return [
        {
            "zone_id": z.zone_id,
            "name": z.zone_name,
            "city_id": c.city_id,
            "city_name": c.city_name,
        }
        for z, c in rows
    ]

def _validate_public_area(
    db: Session,
    city_id: Optional[int] = None,
    zone_id: Optional[int] = None,
):
    """Validate public city and zone filters and their relationship."""

    city = None
    zone = None

    if city_id is not None:
        city = db.query(City).filter(City.city_id == city_id).first()
        if city is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with ID {city_id} does not exist",
            )

    if zone_id is not None:
        zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not exist",
            )

        if city is not None and zone.city_id != city.city_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not belong to city {city_id}",
            )

    return city, zone

def get_area_supply_status(
    db: Session, city_id: Optional[int] = None, zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """Calculate area-specific water supply status based on asset health and operational anomalies."""
    asset_query = db.query(Asset).join(Zone, Asset.zone_id == Zone.zone_id)
    area_name = "All Municipal Areas (Simulated)"
    city = None
    zone = None

    if city_id is not None:
        city = db.query(City).filter(City.city_id == city_id).first()
        if city is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with ID {city_id} does not exist",
            )

    if zone_id is not None:
        zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not exist",
            )
        if city is not None and zone.city_id != city.city_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not belong to city {city_id}",
            )

    if zone is not None:
        zone_city = city or db.query(City).filter(City.city_id == zone.city_id).first()
        area_name = (
            f"{zone_city.city_name} - {zone.zone_name}"
            if zone_city is not None
            else zone.zone_name
        )
        asset_query = asset_query.filter(Asset.zone_id == zone.zone_id)
    elif city is not None:
        area_name = f"{city.city_name} (All Zones)"
        asset_query = asset_query.filter(Zone.city_id == city.city_id)

    assets = asset_query.all()
    total_assets = len(assets)
    operational_assets = sum(1 for a in assets if a.status.lower() == "operational")
    disrupted_assets = total_assets - operational_assets
    asset_ids = [a.asset_id for a in assets]

    # Count active anomalies on these assets
    active_anomalies_count = 0
    if asset_ids:
        active_anomalies_count = (
            db.query(Anomaly)
            .filter(Anomaly.asset_id.in_(asset_ids))
            .filter(Anomaly.status.in_(["Detected", "Active", "Open"]))
            .count()
        )

    # Count active maintenance
    active_maintenance_count = 0
    if asset_ids:
        active_maintenance_count = (
            db.query(MaintenanceRecord)
            .filter(MaintenanceRecord.asset_id.in_(asset_ids))
            .filter(MaintenanceRecord.status.in_(["Scheduled", "In Progress"]))
            .count()
        )

    # Determine status & human-readable message
    if disrupted_assets > 0:
        status_label = "Disrupted"
        message = f"Supply disruption: {disrupted_assets} asset(s) currently non-operational in {area_name}."
    elif active_anomalies_count > 0:
        status_label = "Advisory"
        message = f"Supply advisory: {active_anomalies_count} active operational anomaly/anomalies detected in {area_name}."
    elif active_maintenance_count > 0:
        status_label = "Maintenance"
        message = f"Scheduled maintenance in progress on {active_maintenance_count} asset(s) in {area_name}."
    else:
        status_label = "Normal"
        message = f"Normal supply: All {total_assets} infrastructure assets operating nominally in {area_name}."

    return {
        "area_name": area_name,
        "city_id": city_id,
        "zone_id": zone_id,
        "status": status_label,
        "message": message,
        "total_assets": total_assets,
        "operational_assets": operational_assets,
        "active_anomalies_count": active_anomalies_count,
        "active_maintenance_count": active_maintenance_count,
        "last_updated": datetime.now(),
    }


def get_water_quality_ph(
    db: Session, city_id: Optional[int] = None, zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieve simulated pH status using the configured project reference range."""
    city = None
    zone = None

    if city_id is not None:
        city = db.query(City).filter(City.city_id == city_id).first()
        if city is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"City with ID {city_id} does not exist",
            )

    if zone_id is not None:
        zone = db.query(Zone).filter(Zone.zone_id == zone_id).first()
        if zone is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not exist",
            )
        if city is not None and zone.city_id != city.city_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Zone with ID {zone_id} does not belong to city {city_id}",
            )

    sensor_query = (
        db.query(Sensor, Asset)
        .join(Asset, Sensor.asset_id == Asset.asset_id)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .filter(Sensor.sensor_type == "pH")
    )

    if zone is not None:
        scoped = sensor_query.filter(Asset.zone_id == zone.zone_id).all()
        if not scoped:
            # If this zone has no direct treatment facility/reservoir pH sensor, look in the parent city
            scoped = sensor_query.filter(Zone.city_id == zone.city_id).all()
        sensors_with_assets = scoped
    elif city is not None:
        sensors_with_assets = sensor_query.filter(Zone.city_id == city.city_id).all()
    else:
        sensors_with_assets = sensor_query.all()

    if not sensors_with_assets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No pH sensors are available for the requested area",
        )

    sensor_ids = [s.sensor_id for s, _ in sensors_with_assets]
    sensor_asset_map = {s.sensor_id: a for s, a in sensors_with_assets}

    latest_reading = None
    if sensor_ids:
        latest_reading = (
            db.query(SensorReading)
            .filter(SensorReading.sensor_id.in_(sensor_ids))
            .filter(SensorReading.reading_value_numeric.isnot(None))
            .order_by(
                SensorReading.timestamp.desc(),
                SensorReading.reading_id.desc(),
            )
            .first()
        )

    if latest_reading is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No numeric pH readings are available for the requested area",
        )

    ph_value = float(latest_reading.reading_value_numeric)
    reading_time = latest_reading.timestamp
    asset_obj = sensor_asset_map.get(latest_reading.sensor_id)
    sample_asset = _display_name(asset_obj) if asset_obj else "Water Facility"

    if ph_value < PH_THRESHOLD_MIN:
        status_label = "Acidic Warning"
        is_safe = False
        message = (
            f"pH reading ({ph_value:.2f}) is below the configured project "
            f"reference range ({PH_THRESHOLD_MIN} - {PH_THRESHOLD_MAX})."
        )
    elif ph_value > PH_THRESHOLD_MAX:
        status_label = "Alkaline Warning"
        is_safe = False
        message = (
            f"pH reading ({ph_value:.2f}) exceeds the configured project "
            f"reference range ({PH_THRESHOLD_MIN} - {PH_THRESHOLD_MAX})."
        )
    else:
        status_label = "Normal"
        is_safe = True
        message = (
            f"pH reading ({ph_value:.2f}) is within the configured project "
            f"reference range ({PH_THRESHOLD_MIN} - {PH_THRESHOLD_MAX}). "
            "This pH result does not assess overall drinking-water safety."
        )

    return {
        "parameter": "pH",
        "unit": "pH",
        "ph_value": ph_value,
        "status": status_label,
        "is_safe": is_safe,
        "threshold_min": PH_THRESHOLD_MIN,
        "threshold_max": PH_THRESHOLD_MAX,
        "message": message,
        "sample_asset": sample_asset,
        "timestamp": reading_time,
    }


def get_area_issues(
    db: Session, city_id: Optional[int] = None, zone_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieve active operational issues in the specified area."""

    city, zone = _validate_public_area(db, city_id, zone_id)

    query = (
        db.query(Anomaly, Asset, Zone, City)
        .join(Asset, Anomaly.asset_id == Asset.asset_id)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
        .filter(Anomaly.status.in_(["Detected", "Active", "Open"]))
        .order_by(Anomaly.detected_at.desc())
    )

    if zone is not None:
        query = query.filter(Asset.zone_id == zone.zone_id)
    elif city is not None:
        query = query.filter(Zone.city_id == city.city_id)

    rows = query.limit(50).all()

    return [
        {
            "anomaly_id": anomaly.anomaly_id,
            "anomaly_type": anomaly.anomaly_type,
            "description": anomaly.description,
            "detected_at": anomaly.detected_at,
            "status": anomaly.status,
            "asset_name": _display_name(asset),
            "asset_type": asset.asset_type,
            "zone_name": zone.zone_name,
            "city_name": city.city_name,
        }
        for anomaly, asset, zone, city in rows
    ]


def get_area_maintenance(
    db: Session, city_id: Optional[int] = None, zone_id: Optional[int] = None
) -> List[Dict[str, Any]]:
    """Retrieve scheduled and ongoing public maintenance activities."""

    city, zone = _validate_public_area(db, city_id, zone_id)

    query = (
        db.query(MaintenanceRecord, Asset, Zone, City)
        .join(Asset, MaintenanceRecord.asset_id == Asset.asset_id)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
        .filter(MaintenanceRecord.status.in_(["Scheduled", "In Progress"]))
        .order_by(MaintenanceRecord.maintenance_date.desc())
    )

    if zone is not None:
        query = query.filter(Asset.zone_id == zone.zone_id)
    elif city is not None:
        query = query.filter(Zone.city_id == city.city_id)

    rows = query.limit(50).all()

    return [
        {
            "maintenance_id": record.maintenance_id,
            "asset_name": _display_name(asset),
            "asset_type": asset.asset_type,
            "maintenance_date": record.maintenance_date,
            "maintenance_details": record.maintenance_details,
            "status": record.status,
            "notes": record.notes,
            "zone_name": zone.zone_name,
            "city_name": city.city_name,
        }
        for record, asset, zone, city in rows
    ]

def get_area_infrastructure(
    db: Session, city_id: Optional[int] = None, zone_id: Optional[int] = None
) -> Dict[str, Any]:
    """Retrieve infrastructure breakdown and asset inventory for an area."""

    city, zone = _validate_public_area(db, city_id, zone_id)

    query = (
        db.query(Asset, Zone, City)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
        .order_by(Asset.asset_id.asc())
    )

    if zone is not None:
        query = query.filter(Asset.zone_id == zone.zone_id)
    elif city is not None:
        query = query.filter(Zone.city_id == city.city_id)

    rows = query.all()
    total_count = len(rows)
    operational_count = sum(
        1 for asset, _, _ in rows
        if asset.status.lower() == "operational"
    )

    type_counts: Dict[str, int] = {}
    assets_list = []

    for asset, area_zone, area_city in rows:
        type_counts[asset.asset_type] = (
            type_counts.get(asset.asset_type, 0) + 1
        )
        assets_list.append({
            "asset_id": asset.asset_name,
            "name": _display_name(asset),
            "type": asset.asset_type,
            "status": asset.status,
            "zone_name": area_zone.zone_name,
            "city_name": area_city.city_name,
        })

    return {
        "total_count": total_count,
        "operational_count": operational_count,
        "type_counts": type_counts,
        "assets": assets_list,
    }


def create_public_complaint(
    db: Session, details: str, zone_id: Optional[int] = None
) -> str:
    """Validate complaint submission, generate unique tracking ID, and persist to database."""
    clean_details = (details or "").strip()
    if not clean_details:
        raise HTTPException(
            status_code=422,
            detail="Complaint details are required",
        )
    if len(clean_details) < 5:
        raise HTTPException(
            status_code=422,
            detail="Complaint details must be at least 5 characters long",
        )
    if len(clean_details) > 2000:
        raise HTTPException(
            status_code=422,
            detail="Complaint details must not exceed 2000 characters",
        )

    # Validate zone_id if provided
    if zone_id is not None:
        zone_exists = db.query(Zone).filter(Zone.zone_id == zone_id).first()
        if not zone_exists:
            raise HTTPException(
                status_code=422,
                detail=f"Zone with ID {zone_id} does not exist",
            )

    # Generate unpredictable unique tracking ID
    # Format: CMP-XXXXXXXX-XXXX (e.g. CMP-A7B8C9D0-E1F2)
    max_attempts = 10
    tracking_id = ""
    for _ in range(max_attempts):
        candidate = f"CMP-{secrets.token_hex(4).upper()}-{secrets.token_hex(2).upper()}"
        exists = db.query(Complaint).filter(Complaint.complaint_identification_value == candidate).first()
        if not exists:
            tracking_id = candidate
            break

    if not tracking_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique complaint tracking ID",
        )

    complaint = Complaint(
        complaint_identification_value=tracking_id,
        zone_id=zone_id,
        complaint_details=clean_details,
        status="Submitted",
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return tracking_id


def track_public_complaint(db: Session, tracking_id: str) -> Dict[str, Any]:
    """Retrieve complaint details, resolution, area info, and linked notifications."""
    clean_id = (tracking_id or "").strip()
    complaint = (
        db.query(Complaint)
        .filter(func.upper(Complaint.complaint_identification_value) == clean_id.upper())
        .first()
    )
    if not complaint:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found",
        )

    zone_name = None
    city_name = None
    if complaint.zone_id:
        zone = db.query(Zone).filter(Zone.zone_id == complaint.zone_id).first()
        if zone:
            zone_name = zone.zone_name
            city = db.query(City).filter(City.city_id == zone.city_id).first()
            if city:
                city_name = city.city_name

    notifications = (
        db.query(Notification)
        .filter(Notification.complaint_id == complaint.complaint_id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    return {
        "tracking_id": complaint.complaint_identification_value,
        "details": complaint.complaint_details,
        "status": complaint.status,
        "resolution": complaint.resolution_details,
        "submitted_at": complaint.submitted_at,
        "zone_id": complaint.zone_id,
        "zone_name": zone_name,
        "city_name": city_name,
        "notifications": notifications,
    }
