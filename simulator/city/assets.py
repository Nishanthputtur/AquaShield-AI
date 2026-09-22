"""
Defines water infrastructure asset types and the Asset dataclass
for the AquaShield AI virtual water city.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List


class AssetType(Enum):
    """Types of water infrastructure assets."""

    TREATMENT_FACILITY = "Treatment Facility"
    RESERVOIR = "Reservoir"
    PUMP_STATION = "Pump Station"
    PIPELINE = "Pipeline"
    VALVE = "Valve"


@dataclass
class Asset:
    """
    Represents a single water infrastructure asset.

    Each asset belongs to one city and one zone.
    Sensors are attached directly to the asset's `sensors` list.
    """

    id: str
    name: str
    asset_type: AssetType
    city_id: str
    zone_id: str
    sensors: List = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the basic identity information of the asset."""

        if not self.id.strip():
            raise ValueError("Asset ID cannot be empty.")

        if not self.name.strip():
            raise ValueError("Asset name cannot be empty.")

        if not self.city_id.strip():
            raise ValueError("City ID cannot be empty.")

        if not self.zone_id.strip():
            raise ValueError("Zone ID cannot be empty.")


# ----------------------------------------------------------------------
# Global asset registry
#
# Maps asset_id -> Asset.
#
# This dictionary is populated by create_virtual_city() so that the
# same Asset objects are shared with VirtualCity.assets.
# Sensor modules import ASSETS from this module.
# ----------------------------------------------------------------------
ASSETS: Dict[str, Asset] = {}


def create_assets_for_city(
    city_id: str,
    zone_ids: List[str],
    *,
    treatment_facilities: int = 2,
    reservoirs: int = 2,
    pump_stations: int = 3,
    pipelines: int = 12,
    valves: int = 8,
) -> List[Asset]:
    """
    Create the deterministic infrastructure assets for one city.

    Each city contains:
        - 2 Treatment Facilities
        - 2 Reservoirs
        - 3 Pump Stations
        - 12 Pipelines
        - 8 Valves

    Total assets per city = 27.

    Assets are distributed among the city's four zones
    using round-robin distribution.
    """

    if not city_id.strip():
        raise ValueError("City ID cannot be empty.")

    if len(zone_ids) != 4:
        raise ValueError("Each city must have exactly 4 zones.")

    if len(set(zone_ids)) != len(zone_ids):
        raise ValueError("Zone IDs must be unique.")

    if any(not zone_id.strip() for zone_id in zone_ids):
        raise ValueError("Zone IDs cannot be empty.")

    type_counts = [
        (
            AssetType.TREATMENT_FACILITY,
            treatment_facilities,
            "TF",
        ),
        (
            AssetType.RESERVOIR,
            reservoirs,
            "R",
        ),
        (
            AssetType.PUMP_STATION,
            pump_stations,
            "PS",
        ),
        (
            AssetType.PIPELINE,
            pipelines,
            "P",
        ),
        (
            AssetType.VALVE,
            valves,
            "V",
        ),
    ]

    assets: List[Asset] = []

    for asset_type, count, prefix in type_counts:

        if count < 0:
            raise ValueError(
                f"Asset count cannot be negative: {asset_type.value}"
            )

        for index in range(1, count + 1):

            # Distribute assets across the four zones.
            zone_index = (index - 1) % len(zone_ids)
            zone_id = zone_ids[zone_index]

            # City-specific deterministic ID.
            asset_id = f"{city_id}-{prefix}-{index:03d}"

            asset_name = f"{asset_type.value} {asset_id}"

            asset = Asset(
                id=asset_id,
                name=asset_name,
                asset_type=asset_type,
                city_id=city_id,
                zone_id=zone_id,
            )

            assets.append(asset)

    return assets