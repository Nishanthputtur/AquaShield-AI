"""
Maintenance endpoints for AquaShield AI.

Matching CONTRACT.md Section 4.12 and 4.13.
Authorized for Maintenance Officer only.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import get_current_user, require_role
from backend.app.models.asset import Asset
from backend.app.models.city import City
from backend.app.models.maintenance import MaintenanceRecord
from backend.app.models.user import User
from backend.app.models.zone import Zone
from backend.app.schemas.asset import AssetResponse
from backend.app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceListResponse,
    MaintenanceResponse,
    MaintenanceWithAssetResponse,
)
from backend.app.services.asset_service import _display_name

router = APIRouter(
    prefix="/api/v1/maintenance",
    tags=["maintenance"],
    dependencies=[Depends(require_role("Maintenance Officer"))],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=MaintenanceResponse,
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=MaintenanceResponse,
    include_in_schema=False,
)
def create_maintenance_record(
    payload: MaintenanceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record a maintenance action.

    Authorized for Maintenance Officer only.
    maintenance_officer_id is server-derived from JWT per D04-13.
    """
    asset = (
        db.query(Asset)
        .filter(
            (Asset.asset_name == payload.asset_id)
            | (
                Asset.asset_id == int(payload.asset_id)
                if payload.asset_id.isdigit()
                else False
            )
        )
        .first()
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Referenced asset does not exist",
        )

    record = MaintenanceRecord(
        asset_id=asset.asset_id,
        maintenance_officer_id=current_user.user_id,
        maintenance_date=datetime.now(),
        maintenance_details=payload.maintenance_details,
        status=payload.status,
        notes=payload.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return MaintenanceResponse(
        maintenance_id=record.maintenance_id,
        asset_id=str(asset.asset_name),
        maintenance_officer_id=record.maintenance_officer_id,
        maintenance_date=record.maintenance_date,
        maintenance_details=record.maintenance_details,
        status=record.status,
        notes=record.notes,
    )


@router.get("", response_model=MaintenanceListResponse)
@router.get("/", response_model=MaintenanceListResponse, include_in_schema=False)
def list_maintenance_records(db: Session = Depends(get_db)):
    """Retrieve all maintenance records with embedded asset context.

    Authorized for Maintenance Officer only.
    Returns all records regardless of who created them per D04-14.
    """
    rows = (
        db.query(MaintenanceRecord, Asset, Zone, City)
        .join(Asset, MaintenanceRecord.asset_id == Asset.asset_id)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
        .order_by(MaintenanceRecord.maintenance_id.asc())
        .all()
    )

    items = []
    for record, asset, zone, city in rows:
        asset_resp = AssetResponse(
            asset_id=str(asset.asset_name),
            name=_display_name(asset),
            type=str(asset.asset_type),
            status=str(asset.status),
            city_name=str(city.city_name),
            zone_name=str(zone.zone_name),
        )
        items.append(
            MaintenanceWithAssetResponse(
                maintenance_id=record.maintenance_id,
                asset_id=str(asset.asset_name),
                maintenance_officer_id=record.maintenance_officer_id,
                maintenance_date=record.maintenance_date,
                maintenance_details=record.maintenance_details,
                status=record.status,
                notes=record.notes,
                asset=asset_resp,
            )
        )

    return MaintenanceListResponse(
        maintenance_records=items, total=len(items)
    )
