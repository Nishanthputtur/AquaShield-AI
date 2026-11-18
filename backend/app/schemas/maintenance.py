"""
Maintenance Pydantic schemas for AquaShield AI.

Matching CONTRACT.md Section 4.12 and 4.13.
CRITICAL: Contains no password_hash or auth internals.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.asset import AssetResponse


class MaintenanceCreate(BaseModel):
    """Payload for recording a maintenance action.

    Strict: extra fields (such as maintenance_officer_id) are rejected with HTTP 422.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(..., min_length=1)
    maintenance_details: str = Field(..., min_length=1)
    status: str = Field(..., min_length=1, max_length=30)
    notes: Optional[str] = None


class MaintenanceResponse(BaseModel):
    """Maintenance record response without user internals or password hash.

    Matches CONTRACT.md Section 4.12.
    """

    model_config = ConfigDict(from_attributes=True)

    maintenance_id: int
    asset_id: str
    maintenance_officer_id: int
    maintenance_date: datetime
    maintenance_details: str
    status: str
    notes: Optional[str] = None


class MaintenanceWithAssetResponse(MaintenanceResponse):
    """Maintenance record with embedded asset context matching CONTRACT.md Section 4.13."""

    asset: AssetResponse


class MaintenanceListResponse(BaseModel):
    """Collection response for maintenance records matching CONTRACT.md Section 4.13."""

    maintenance_records: List[MaintenanceWithAssetResponse]
    total: int
