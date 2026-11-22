"""
Public Portal API endpoints for AquaShield AI.

Provides unauthenticated public access for municipal citizens:
- Virtual city and zone discovery
- Area-specific water supply status
- Area-specific operational issues & anomalies
- Area-specific maintenance notices (sanitized)
- Area-specific infrastructure summary
- Drinking water quality status based on pH (approved thresholds 6.5 - 8.5)
- Public municipal announcements and notifications
- Public complaint submission (with optional zone selection) and tracking
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.schemas.complaint import (
    AreaSupplyStatusResponse,
    ComplaintCreateRequest,
    ComplaintTrackResponse,
    InfrastructureOverviewResponse,
    NotificationResponse,
    PublicCityResponse,
    PublicIssueItem,
    PublicMaintenanceItem,
    PublicZoneResponse,
    WaterQualityResponse,
)
from backend.app.services.complaint_service import (
    create_public_complaint,
    get_area_infrastructure,
    get_area_issues,
    get_area_maintenance,
    get_area_supply_status,
    get_public_cities,
    get_public_notifications,
    get_public_zones,
    get_water_quality_ph,
    track_public_complaint,
)

router = APIRouter(prefix="/api/v1/public", tags=["Public Portal"])


@router.get("/cities", response_model=List[PublicCityResponse])
def list_cities(db: Session = Depends(get_db)):
    """Retrieve all simulated cities with their operational zones."""
    return get_public_cities(db)


@router.get("/zones", response_model=List[PublicZoneResponse])
def list_zones(
    city_id: Optional[int] = Query(None, description="Filter zones by city ID"),
    db: Session = Depends(get_db),
):
    """Retrieve operational zones, optionally filtered by city ID."""
    return get_public_zones(db, city_id=city_id)


@router.get("/status", response_model=AreaSupplyStatusResponse)
def get_supply_status(
    city_id: Optional[int] = Query(None, description="City ID"),
    zone_id: Optional[int] = Query(None, description="Zone ID"),
    db: Session = Depends(get_db),
):
    """Retrieve live area-specific water supply status."""
    return get_area_supply_status(db, city_id=city_id, zone_id=zone_id)


@router.get("/water-quality", response_model=WaterQualityResponse)
def get_water_quality(
    city_id: Optional[int] = Query(None, description="City ID"),
    zone_id: Optional[int] = Query(None, description="Zone ID"),
    db: Session = Depends(get_db),
):
    """Retrieve water quality status based on pH using approved project thresholds (6.5 - 8.5)."""
    return get_water_quality_ph(db, city_id=city_id, zone_id=zone_id)


@router.get("/issues", response_model=List[PublicIssueItem])
def list_area_issues(
    city_id: Optional[int] = Query(None, description="City ID"),
    zone_id: Optional[int] = Query(None, description="Zone ID"),
    db: Session = Depends(get_db),
):
    """Retrieve active area operational anomalies and issues."""
    return get_area_issues(db, city_id=city_id, zone_id=zone_id)


@router.get("/maintenance", response_model=List[PublicMaintenanceItem])
def list_area_maintenance(
    city_id: Optional[int] = Query(None, description="City ID"),
    zone_id: Optional[int] = Query(None, description="Zone ID"),
    db: Session = Depends(get_db),
):
    """Retrieve sanitized scheduled and ongoing maintenance activities for an area."""
    return get_area_maintenance(db, city_id=city_id, zone_id=zone_id)


@router.get("/infrastructure", response_model=InfrastructureOverviewResponse)
def get_infrastructure_overview(
    city_id: Optional[int] = Query(None, description="City ID"),
    zone_id: Optional[int] = Query(None, description="Zone ID"),
    db: Session = Depends(get_db),
):
    """Retrieve infrastructure breakdown and asset summary for an area."""
    return get_area_infrastructure(db, city_id=city_id, zone_id=zone_id)


@router.get("/notifications", response_model=List[NotificationResponse])
def list_announcements(db: Session = Depends(get_db)):
    """Retrieve public municipal announcements and advisories."""
    return get_public_notifications(db)


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def submit_complaint(
    payload: ComplaintCreateRequest,
    db: Session = Depends(get_db),
):
    """Submit a public water issue complaint with optional zone selection.
    
    Generates a cryptographically unpredictable unique tracking ID.
    """
    tracking_id = create_public_complaint(
        db=db,
        details=payload.details,
        zone_id=payload.zone_id,
    )
    return {"message": "Complaint submitted", "tracking_id": tracking_id}


@router.get("/complaints/{tracking_id}", response_model=ComplaintTrackResponse)
def track_complaint(
    tracking_id: str,
    db: Session = Depends(get_db),
):
    """Track a previously filed complaint by tracking ID."""
    return track_public_complaint(db=db, tracking_id=tracking_id)
