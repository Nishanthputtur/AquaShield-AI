"""
Asset definitions for the AquaShield AI water distribution simulation.

Contains the frozen set of 108 assets:

- 8 Treatment Facilities
- 8 Reservoirs
- 12 Pump Stations
- 48 Pipelines
- 32 Valves
"""

from enum import Enum
from typing import Dict, List


class AssetType(str, Enum):
    """Types of infrastructure assets."""

    TREATMENT_FACILITY = "Treatment Facility"
    RESERVOIR = "Reservoir"
    PUMP_STATION = "Pump Station"
    PIPELINE = "Pipeline"
    VALVE = "Valve"


class AssetStatus(str, Enum):
    """Operational status of an asset."""

    OPERATIONAL = "Operational"
    WARNING = "Warning"
    MAINTENANCE_REQUIRED = "Maintenance Required"
    FAILED = "Failed"
    OFFLINE = "Offline"


class AssetCondition(str, Enum):
    """Physical condition of an asset."""

    EXCELLENT = "Excellent"
    GOOD = "Good"
    MODERATE = "Moderate"
    POOR = "Poor"
    CRITICAL = "Critical"


class Asset:
    """Represents one infrastructure asset."""

    def __init__(
        self,
        asset_id: str,
        asset_type: str,
        city_id: str,
        zone_id: str,
        status: str = AssetStatus.OPERATIONAL,
        condition: str = AssetCondition.GOOD
    ):
        self.asset_id = asset_id
        self.asset_type = asset_type
        self.city_id = city_id
        self.zone_id = zone_id
        self.status = status
        self.condition = condition

        # Sensors will be attached during sensor initialization.
        self.sensors = []

        # Additional asset information.
        self.metadata = {}

    def __repr__(self) -> str:
        return (
            f"Asset("
            f"{self.asset_id}, "
            f"{self.asset_type}, "
            f"{self.zone_id}"
            f")"
        )


# ---------------------------------------------------------------------------
# FROZEN ASSET CONFIGURATION
# ---------------------------------------------------------------------------

# Each entry:
#
# (
#     asset_id,
#     asset_type,
#     city_id,
#     zone_id
# )
#
# Total = 108 assets

ASSET_CONFIG = [

    # ============================================================
    # TREATMENT FACILITIES
    # 8 total, 2 per city
    # ============================================================

    ("TF-001", AssetType.TREATMENT_FACILITY, "ZORAWARPUR", "Z-01"),
    ("TF-002", AssetType.TREATMENT_FACILITY, "ZORAWARPUR", "Z-03"),

    ("TF-003", AssetType.TREATMENT_FACILITY, "AMARANAGAR", "Z-05"),
    ("TF-004", AssetType.TREATMENT_FACILITY, "AMARANAGAR", "Z-07"),

    ("TF-005", AssetType.TREATMENT_FACILITY, "RAJATGIRI", "Z-09"),
    ("TF-006", AssetType.TREATMENT_FACILITY, "RAJATGIRI", "Z-11"),

    ("TF-007", AssetType.TREATMENT_FACILITY, "RAJATPUR", "Z-13"),
    ("TF-008", AssetType.TREATMENT_FACILITY, "RAJATPUR", "Z-15"),

    # ============================================================
    # RESERVOIRS
    # 8 total, 2 per city
    # ============================================================

    ("R-001", AssetType.RESERVOIR, "ZORAWARPUR", "Z-01"),
    ("R-002", AssetType.RESERVOIR, "ZORAWARPUR", "Z-03"),

    ("R-003", AssetType.RESERVOIR, "AMARANAGAR", "Z-05"),
    ("R-004", AssetType.RESERVOIR, "AMARANAGAR", "Z-07"),

    ("R-005", AssetType.RESERVOIR, "RAJATGIRI", "Z-09"),
    ("R-006", AssetType.RESERVOIR, "RAJATGIRI", "Z-11"),

    ("R-007", AssetType.RESERVOIR, "RAJATPUR", "Z-13"),
    ("R-008", AssetType.RESERVOIR, "RAJATPUR", "Z-15"),

    # ============================================================
    # PUMP STATIONS
    # 12 total, 3 per city
    # ============================================================

    ("PS-001", AssetType.PUMP_STATION, "ZORAWARPUR", "Z-01"),
    ("PS-002", AssetType.PUMP_STATION, "ZORAWARPUR", "Z-02"),
    ("PS-003", AssetType.PUMP_STATION, "ZORAWARPUR", "Z-03"),

    ("PS-004", AssetType.PUMP_STATION, "AMARANAGAR", "Z-05"),
    ("PS-005", AssetType.PUMP_STATION, "AMARANAGAR", "Z-06"),
    ("PS-006", AssetType.PUMP_STATION, "AMARANAGAR", "Z-07"),

    ("PS-007", AssetType.PUMP_STATION, "RAJATGIRI", "Z-09"),
    ("PS-008", AssetType.PUMP_STATION, "RAJATGIRI", "Z-10"),
    ("PS-009", AssetType.PUMP_STATION, "RAJATGIRI", "Z-11"),

    ("PS-010", AssetType.PUMP_STATION, "RAJATPUR", "Z-13"),
    ("PS-011", AssetType.PUMP_STATION, "RAJATPUR", "Z-14"),
    ("PS-012", AssetType.PUMP_STATION, "RAJATPUR", "Z-15"),

    # ============================================================
    # PIPELINES
    # 48 total, 3 per zone
    # ============================================================

    # Zorawarpur
    ("PL-001", AssetType.PIPELINE, "ZORAWARPUR", "Z-01"),
    ("PL-002", AssetType.PIPELINE, "ZORAWARPUR", "Z-01"),
    ("PL-003", AssetType.PIPELINE, "ZORAWARPUR", "Z-01"),

    ("PL-004", AssetType.PIPELINE, "ZORAWARPUR", "Z-02"),
    ("PL-005", AssetType.PIPELINE, "ZORAWARPUR", "Z-02"),
    ("PL-006", AssetType.PIPELINE, "ZORAWARPUR", "Z-02"),

    ("PL-007", AssetType.PIPELINE, "ZORAWARPUR", "Z-03"),
    ("PL-008", AssetType.PIPELINE, "ZORAWARPUR", "Z-03"),
    ("PL-009", AssetType.PIPELINE, "ZORAWARPUR", "Z-03"),

    ("PL-010", AssetType.PIPELINE, "ZORAWARPUR", "Z-04"),
    ("PL-011", AssetType.PIPELINE, "ZORAWARPUR", "Z-04"),
    ("PL-012", AssetType.PIPELINE, "ZORAWARPUR", "Z-04"),

    # Amaranagar
    ("PL-013", AssetType.PIPELINE, "AMARANAGAR", "Z-05"),
    ("PL-014", AssetType.PIPELINE, "AMARANAGAR", "Z-05"),
    ("PL-015", AssetType.PIPELINE, "AMARANAGAR", "Z-05"),

    ("PL-016", AssetType.PIPELINE, "AMARANAGAR", "Z-06"),
    ("PL-017", AssetType.PIPELINE, "AMARANAGAR", "Z-06"),
    ("PL-018", AssetType.PIPELINE, "AMARANAGAR", "Z-06"),

    ("PL-019", AssetType.PIPELINE, "AMARANAGAR", "Z-07"),
    ("PL-020", AssetType.PIPELINE, "AMARANAGAR", "Z-07"),
    ("PL-021", AssetType.PIPELINE, "AMARANAGAR", "Z-07"),

    ("PL-022", AssetType.PIPELINE, "AMARANAGAR", "Z-08"),
    ("PL-023", AssetType.PIPELINE, "AMARANAGAR", "Z-08"),
    ("PL-024", AssetType.PIPELINE, "AMARANAGAR", "Z-08"),

    # Rajatgiri
    ("PL-025", AssetType.PIPELINE, "RAJATGIRI", "Z-09"),
    ("PL-026", AssetType.PIPELINE, "RAJATGIRI", "Z-09"),
    ("PL-027", AssetType.PIPELINE, "RAJATGIRI", "Z-09"),

    ("PL-028", AssetType.PIPELINE, "RAJATGIRI", "Z-10"),
    ("PL-029", AssetType.PIPELINE, "RAJATGIRI", "Z-10"),
    ("PL-030", AssetType.PIPELINE, "RAJATGIRI", "Z-10"),

    ("PL-031", AssetType.PIPELINE, "RAJATGIRI", "Z-11"),
    ("PL-032", AssetType.PIPELINE, "RAJATGIRI", "Z-11"),
    ("PL-033", AssetType.PIPELINE, "RAJATGIRI", "Z-11"),

    ("PL-034", AssetType.PIPELINE, "RAJATGIRI", "Z-12"),
    ("PL-035", AssetType.PIPELINE, "RAJATGIRI", "Z-12"),
    ("PL-036", AssetType.PIPELINE, "RAJATGIRI", "Z-12"),

    # Rajatpur
    ("PL-037", AssetType.PIPELINE, "RAJATPUR", "Z-13"),
    ("PL-038", AssetType.PIPELINE, "RAJATPUR", "Z-13"),
    ("PL-039", AssetType.PIPELINE, "RAJATPUR", "Z-13"),

    ("PL-040", AssetType.PIPELINE, "RAJATPUR", "Z-14"),
    ("PL-041", AssetType.PIPELINE, "RAJATPUR", "Z-14"),
    ("PL-042", AssetType.PIPELINE, "RAJATPUR", "Z-14"),

    ("PL-043", AssetType.PIPELINE, "RAJATPUR", "Z-15"),
    ("PL-044", AssetType.PIPELINE, "RAJATPUR", "Z-15"),
    ("PL-045", AssetType.PIPELINE, "ZORAWARPUR", "Z-15"),

    ("PL-046", AssetType.PIPELINE, "RAJATPUR", "Z-16"),
    ("PL-047", AssetType.PIPELINE, "RAJATPUR", "Z-16"),
    ("PL-048", AssetType.PIPELINE, "RAJATPUR", "Z-16"),

    # ============================================================
    # VALVES
    # 32 total, 2 per zone
    # ============================================================

    # Zorawarpur
    ("V-001", AssetType.VALVE, "ZORAWARPUR", "Z-01"),
    ("V-002", AssetType.VALVE, "ZORAWARPUR", "Z-01"),

    ("V-003", AssetType.VALVE, "ZORAWARPUR", "Z-02"),
    ("V-004", AssetType.VALVE, "ZORAWARPUR", "Z-02"),

    ("V-005", AssetType.VALVE, "ZORAWARPUR", "Z-03"),
    ("V-006", AssetType.VALVE, "ZORAWARPUR", "Z-03"),

    ("V-007", AssetType.VALVE, "ZORAWARPUR", "Z-04"),
    ("V-008", AssetType.VALVE, "ZORAWARPUR", "Z-04"),

    # Amaranagar
    ("V-009", AssetType.VALVE, "AMARANAGAR", "Z-05"),
    ("V-010", AssetType.VALVE, "AMARANAGAR", "Z-05"),

    ("V-011", AssetType.VALVE, "AMARANAGAR", "Z-06"),
    ("V-012", AssetType.VALVE, "AMARANAGAR", "Z-06"),

    ("V-013", AssetType.VALVE, "AMARANAGAR", "Z-07"),
    ("V-014", AssetType.VALVE, "AMARANAGAR", "Z-07"),

    ("V-015", AssetType.VALVE, "AMARANAGAR", "Z-08"),
    ("V-016", AssetType.VALVE, "AMARANAGAR", "Z-08"),

    # Rajatgiri
    ("V-017", AssetType.VALVE, "RAJATGIRI", "Z-09"),
    ("V-018", AssetType.VALVE, "RAJATGIRI", "Z-09"),

    ("V-019", AssetType.VALVE, "RAJATGIRI", "Z-10"),
    ("V-020", AssetType.VALVE, "RAJATGIRI", "Z-10"),

    ("V-021", AssetType.VALVE, "RAJATGIRI", "Z-11"),
    ("V-022", AssetType.VALVE, "RAJATGIRI", "Z-11"),

    ("V-023", AssetType.VALVE, "RAJATGIRI", "Z-12"),
    ("V-024", AssetType.VALVE, "RAJATGIRI", "Z-12"),

    # Rajatpur
    ("V-025", AssetType.VALVE, "RAJATPUR", "Z-13"),
    ("V-026", AssetType.VALVE, "RAJATPUR", "Z-13"),

    ("V-027", AssetType.VALVE, "RAJATPUR", "Z-14"),
    ("V-028", AssetType.VALVE, "RAJATPUR", "Z-14"),

    ("V-029", AssetType.VALVE, "RAJATPUR", "Z-15"),
    ("V-030", AssetType.VALVE, "RAJATPUR", "Z-15"),

    ("V-031", AssetType.VALVE, "RAJATPUR", "Z-16"),
    ("V-032", AssetType.VALVE, "RAJATPUR", "Z-16"),
]


def create_assets() -> Dict[str, Asset]:
    """Create all frozen assets."""

    assets = {}

    for asset_id, asset_type, city_id, zone_id in ASSET_CONFIG:
        asset = Asset(
            asset_id=asset_id,
            asset_type=asset_type.value,
            city_id=city_id,
            zone_id=zone_id
        )

        assets[asset_id] = asset

    return assets


# Global asset registry

ASSETS = create_assets()


def get_assets_by_zone(zone_id: str) -> List[Asset]:
    """Return all assets belonging to a zone."""

    return [
        asset
        for asset in ASSETS.values()
        if asset.zone_id == zone_id
    ]


def get_assets_by_type(asset_type: str) -> List[Asset]:
    """Return all assets of a given type."""

    return [
        asset
        for asset in ASSETS.values()
        if asset.asset_type == asset_type
    ]


def get_assets_by_city(city_id: str) -> List[Asset]:
    """Return all assets belonging to a city."""

    return [
        asset
        for asset in ASSETS.values()
        if asset.city_id == city_id
    ]


def verify_asset_counts() -> Dict[str, int]:
    """Verify the frozen asset counts."""

    counts = {}

    for asset in ASSETS.values():
        counts[asset.asset_type] = (
            counts.get(asset.asset_type, 0) + 1
        )

    expected = {
        AssetType.TREATMENT_FACILITY.value: 8,
        AssetType.RESERVOIR.value: 8,
        AssetType.PUMP_STATION.value: 12,
        AssetType.PIPELINE.value: 48,
        AssetType.VALVE.value: 32
    }

    assert counts == expected, (
        f"Asset count mismatch: {counts} != {expected}"
    )

    assert len(ASSETS) == 108, (
        f"Total asset count mismatch: {len(ASSETS)} != 108"
    )

    return counts