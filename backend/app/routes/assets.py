"""
Asset lookup endpoints for AquaShield AI.

Matching CONTRACT.md Section 4.9.
Authorized role: Field Inspector only.
Single lookup only per D04-05; no list endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import require_role
from backend.app.models.asset import Asset
from backend.app.models.city import City
from backend.app.models.zone import Zone
from backend.app.schemas.asset import AssetResponse

router = APIRouter(
    prefix="/api/v1/assets",
    tags=["assets"],
    dependencies=[Depends(require_role("Field Inspector"))],
)


@router.get("/{id}", response_model=AssetResponse)
def get_asset_by_id(id: str, db: Session = Depends(get_db)):
    """Retrieve single known asset by id.

    Authorized for Field Inspector role only.
    Returns exact CONTRACT.md Section 4.9 six-field response.
    """
    query = (
        db.query(Asset, Zone, City)
        .join(Zone, Asset.zone_id == Zone.zone_id)
        .join(City, Zone.city_id == City.city_id)
    )

    if id.isdigit():
        row = query.filter(
            (Asset.asset_id == int(id)) | (Asset.asset_name == id)
        ).first()
    else:
        row = query.filter(Asset.asset_name == id).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resource not found",
        )

    asset, zone, city = row
    return AssetResponse(
        asset_id=str(asset.asset_name),
        name=str(asset.asset_name),
        type=str(asset.asset_type),
        status=str(asset.status),
        city_name=str(city.city_name),
        zone_name=str(zone.zone_name),
    )
