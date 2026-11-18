"""
Inspection Pydantic schemas for AquaShield AI.

Matching CONTRACT.md Section 4.10 and 4.11.
CRITICAL: Contains no password_hash or auth internals.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.asset import AssetResponse


class InspectionCreate(BaseModel):
    """Payload for submitting an inspection.

    Strict: extra fields (such as inspector_id) are rejected with HTTP 422.
    """

    model_config = ConfigDict(extra="forbid")

    asset_id: str = Field(..., min_length=1)
    findings: str = Field(..., min_length=1)
    condition: Optional[str] = None


class InspectionResponse(BaseModel):
    """Inspection record response without user internals or password hash.

    Matches CONTRACT.md Section 4.10.
    """

    model_config = ConfigDict(from_attributes=True)

    inspection_id: int
    asset_id: str
    inspector_id: int
    inspection_date: datetime
    findings: str
    condition: Optional[str] = None
    status: Optional[str] = None


class InspectionWithAssetResponse(InspectionResponse):
    """Inspection record with embedded asset context matching CONTRACT.md Section 4.11."""

    asset: AssetResponse


class InspectionListResponse(BaseModel):
    """Collection response for inspection records matching CONTRACT.md Section 4.11."""

    inspections: List[InspectionWithAssetResponse]
    total: int
