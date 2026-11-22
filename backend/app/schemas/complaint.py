"""
Public Portal and Complaint Pydantic schemas for AquaShield AI.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ComplaintCreateRequest(BaseModel):
    """Payload for submitting a public complaint."""
    model_config = ConfigDict(extra="forbid")

    details: str = Field(..., min_length=5, max_length=2000, description="Description of the water issue")
    zone_id: Optional[int] = Field(None, description="Optional municipal zone ID")


class NotificationResponse(BaseModel):
    """Public announcement or notification item."""
    model_config = ConfigDict(from_attributes=True)

    notification_id: int
    title: str
    message: str
    notification_type: str
    created_at: datetime


class ComplaintTrackResponse(BaseModel):
    """Public complaint status response matching existing contract and extended with details."""
    model_config = ConfigDict(from_attributes=True)

    tracking_id: str
    details: str
    status: str
    resolution: Optional[str] = None
    submitted_at: Optional[datetime] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    city_name: Optional[str] = None
    notifications: List[NotificationResponse] = []


class PublicZoneResponse(BaseModel):
    """Zone information item for public portal."""
    model_config = ConfigDict(from_attributes=True)

    zone_id: int
    name: str
    city_id: Optional[int] = None
    city_name: Optional[str] = None


class PublicCityResponse(BaseModel):
    """City information with nested zones for public portal."""
    model_config = ConfigDict(from_attributes=True)

    city_id: int
    city_name: str
    description: Optional[str] = None
    zones: List[PublicZoneResponse] = []


class AreaSupplyStatusResponse(BaseModel):
    """Area-specific water supply status."""
    area_name: str
    city_id: Optional[int] = None
    zone_id: Optional[int] = None
    status: str
    message: str
    total_assets: int
    operational_assets: int
    active_anomalies_count: int
    active_maintenance_count: int
    last_updated: datetime


class WaterQualityResponse(BaseModel):
    """Simulated pH assessment using the configured project reference range."""
    parameter: str = "pH"
    unit: str = "pH"
    ph_value: float
    status: str
    is_safe: bool = Field(
        description=(
            "Whether the pH value is within the configured project reference "
            "range; this is not a complete drinking-water safety assessment."
        )
    )
    threshold_min: float = 6.5
    threshold_max: float = 8.5
    message: str
    sample_asset: Optional[str] = None
    timestamp: datetime


class PublicIssueItem(BaseModel):
    """Area-specific operational issue / anomaly."""
    anomaly_id: int
    anomaly_type: str
    description: Optional[str] = None
    detected_at: datetime
    status: Optional[str] = None
    asset_name: str
    asset_type: str
    zone_name: Optional[str] = None
    city_name: Optional[str] = None


class PublicMaintenanceItem(BaseModel):
    """Area-specific maintenance activity (sanitized for public view)."""
    maintenance_id: int
    asset_name: str
    asset_type: str
    maintenance_date: datetime
    maintenance_details: str
    status: str
    notes: Optional[str] = None
    zone_name: Optional[str] = None
    city_name: Optional[str] = None


class PublicAssetItem(BaseModel):
    """Public infrastructure asset summary."""
    asset_id: str
    name: str
    type: str
    status: str
    zone_name: Optional[str] = None
    city_name: Optional[str] = None


class InfrastructureOverviewResponse(BaseModel):
    """Area infrastructure overview and breakdown."""
    total_count: int
    operational_count: int
    type_counts: Dict[str, int]
    assets: List[PublicAssetItem]
