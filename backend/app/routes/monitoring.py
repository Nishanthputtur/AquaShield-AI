"""
Monitoring endpoints for AquaShield AI.

Matching CONTRACT.md Section 4.8.
Authorized role: Engineer only.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import require_role
from backend.app.schemas.asset import (
    AssetResponse,
    MonitoringReadingsResponse,
    ReadingItem,
)
from backend.app.services.asset_service import _display_name
from backend.app.services.simulation_service import simulation_service

router = APIRouter(
    prefix="/api/v1/monitoring",
    tags=["monitoring"],
    dependencies=[Depends(require_role("Engineer"))],
)


@router.get("/readings", response_model=MonitoringReadingsResponse)
def get_monitoring_readings(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Retrieve virtual sensor readings with inline asset context.

    Authorized for Engineer role only. Returns exact CONTRACT.md Section 4.8 fields.
    """
    from simulator.city.assets import ASSETS
    from simulator.city.virtual_city import create_virtual_city
    from simulator.sensors import initialize_sensors

    if not ASSETS:
        create_virtual_city()
    initialize_sensors()

    raw_readings = simulation_service.get_engineer_readings(db=db, limit=limit)

    formatted_readings = []
    for r in raw_readings:
        asset_info = r.get("asset")
        asset_resp = None
        if asset_info:
            asset_resp = AssetResponse(
                asset_id=str(r.get("asset_id", asset_info.get("name"))),
                name=_display_name(asset_info),
                type=str(asset_info.get("type")),
                status=str(asset_info.get("status")),
                city_name=str(asset_info.get("city_name")),
                zone_name=str(asset_info.get("zone_name")),
            )
        formatted_readings.append(
            ReadingItem(
                sensor_id=str(r["sensor_id"]),
                asset_id=str(r["asset_id"]),
                parameter=str(r["parameter"]),
                value=r["value"],
                unit=str(r["unit"]),
                timestamp=str(r["timestamp"]),
                asset=asset_resp,
            )
        )

    return MonitoringReadingsResponse(readings=formatted_readings)
