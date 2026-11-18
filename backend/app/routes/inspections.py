"""
Inspection endpoints for AquaShield AI.

Matching CONTRACT.md Section 4.10 and 4.11.
POST authorized for Field Inspector only.
GET authorized for Maintenance Officer only.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import get_current_user, require_role
from backend.app.models.asset import Asset
from backend.app.models.city import City
from backend.app.models.maintenance import Inspection
from backend.app.models.user import User
from backend.app.models.zone import Zone
from backend.app.schemas.asset import AssetResponse
from backend.app.schemas.inspection import (
    InspectionCreate,
    InspectionListResponse,
    InspectionResponse,
    InspectionWithAssetResponse,
)
from backend.app.services.asset_service import _display_name

router = APIRouter(
    prefix="/api/v1/inspections",
    tags=["inspections"],
)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=InspectionResponse,
    dependencies=[Depends(require_role("Field Inspector"))],
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=InspectionResponse,
    include_in_schema=False,
    dependencies=[Depends(require_role("Field Inspector"))],
)
def create_inspection(
    payload: InspectionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit an asset inspection.

    Authorized for Field Inspector only.
    inspector_id is server-derived from JWT per D04-12.
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

    inspection = Inspection(
        asset_id=asset.asset_id,
        inspector_id=current_user.user_id,
        inspection_date=datetime.now(),
        findings=payload.findings,
        condition=payload.condition,
        status="recorded",
    )
    db.add(inspection)
    db.commit()
    db.refresh(inspection)

    return InspectionResponse(
        inspection_id=inspection.inspection_id,
        asset_id=str(asset.asset_name),
        inspector_id=inspection.inspector_id,
        inspection_date=inspection.inspection_date,
        findings=inspection.findings,
        condition=inspection.condition,
        status=inspection.status,
    )


@router.get(
    "",
    response_model=InspectionListResponse,
    dependencies=[Depends(require_role("Maintenance Officer"))],
)
@router.get(
    "/",
    response_model=InspectionListResponse,
    include_in_schema=False,
    dependencies=[Depends(require_role("Maintenance Officer"))],
)
def list_inspections(db: Session = Depends(get_db)):
    """Retrieve all inspection records with embedded asset context.

    Authorized for Maintenance Officer only.
    """
    rows = (
        db.query(Inspection, Asset, Zone, City)
        .join(Asset, Inspection.asset_id == Asset.asset_id)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
        .order_by(Inspection.inspection_id.asc())
        .all()
    )

    items = []
    for inspection, asset, zone, city in rows:
        asset_resp = AssetResponse(
            asset_id=str(asset.asset_name),
            name=_display_name(asset),
            type=str(asset.asset_type),
            status=str(asset.status),
            city_name=str(city.city_name),
            zone_name=str(zone.zone_name),
        )
        items.append(
            InspectionWithAssetResponse(
                inspection_id=inspection.inspection_id,
                asset_id=str(asset.asset_name),
                inspector_id=inspection.inspector_id,
                inspection_date=inspection.inspection_date,
                findings=inspection.findings,
                condition=inspection.condition,
                status=inspection.status,
                asset=asset_resp,
            )
        )

    return InspectionListResponse(inspections=items, total=len(items))
