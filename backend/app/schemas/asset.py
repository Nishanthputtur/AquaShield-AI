"""
Asset and monitoring Pydantic schemas for AquaShield AI.

Matching CONTRACT.md Section 4.8 and 4.9.
CRITICAL: Contains no password_hash or auth internals.
"""

from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    """Single asset representation matching CONTRACT.md Section 4.9.

    Contains exactly six approved fields:
    asset_id, name, type, status, city_name, zone_name.
    """

    model_config = ConfigDict(from_attributes=True)

    asset_id: str
    name: str
    type: str
    status: str
    city_name: str
    zone_name: str


class ReadingItem(BaseModel):
    """Virtual sensor reading item with inline asset context.

    Matches CONTRACT.md Section 4.8.
    """

    model_config = ConfigDict(from_attributes=True)

    sensor_id: str
    asset_id: str
    parameter: str
    value: Union[float, int, str]
    unit: str
    timestamp: str
    asset: Optional[AssetResponse] = None


class MonitoringReadingsResponse(BaseModel):
    """Collection response for virtual sensor readings matching CONTRACT.md Section 4.8."""

    readings: List[ReadingItem]
