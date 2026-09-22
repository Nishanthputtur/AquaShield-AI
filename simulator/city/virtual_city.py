"""
Assembly of the complete virtual water city
for the AquaShield AI project.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .assets import ASSETS, Asset, create_assets_for_city
from .zones import Zone
from .cities import City, create_cities


@dataclass
class VirtualCity:
    """
    Top-level container for the complete virtual water system.

    Contains:
        - 4 cities
        - 16 zones
        - 108 assets
    """

    cities: List[City] = field(default_factory=list)
    zones: List[Zone] = field(default_factory=list)
    assets: List[Asset] = field(default_factory=list)

    # Internal indexes for fast lookup.
    _asset_by_id: Dict[str, Asset] = field(
        default_factory=dict,
        init=False,
        repr=False
    )

    _zone_by_id: Dict[str, Zone] = field(
        default_factory=dict,
        init=False,
        repr=False
    )

    def __post_init__(self) -> None:
        """Build lookup indexes after the object is created."""

        self._rebuild_indexes()

    def _rebuild_indexes(self) -> None:
        """Rebuild internal dictionaries for fast lookups."""

        self._asset_by_id = {
            asset.id: asset
            for asset in self.assets
        }

        self._zone_by_id = {
            zone.id: zone
            for zone in self.zones
        }

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Return an asset by its ID."""

        return self._asset_by_id.get(asset_id)

    def get_zone(self, zone_id: str) -> Optional[Zone]:
        """Return a zone by its ID."""

        return self._zone_by_id.get(zone_id)

    def get_city(self, city_id: str) -> Optional[City]:
        """Return a city by its ID."""

        for city in self.cities:
            if city.id == city_id:
                return city

        return None

    def get_assets_by_zone(self, zone_id: str) -> List[Asset]:
        """Return all assets belonging to a given zone."""

        zone = self.get_zone(zone_id)

        if zone is None:
            return []

        assets: List[Asset] = []

        for asset_id in zone.asset_ids:
            asset = self.get_asset(asset_id)

            if asset is not None:
                assets.append(asset)

        return assets

    def get_zones_by_city(self, city_id: str) -> List[Zone]:
        """Return all zones belonging to a given city."""

        city = self.get_city(city_id)

        if city is None:
            return []

        zones: List[Zone] = []

        for zone_id in city.zone_ids:
            zone = self.get_zone(zone_id)

            if zone is not None:
                zones.append(zone)

        return zones

    def get_assets_by_city(self, city_id: str) -> List[Asset]:
        """Return all assets belonging to a given city."""

        zones = self.get_zones_by_city(city_id)

        assets: List[Asset] = []

        for zone in zones:
            assets.extend(self.get_assets_by_zone(zone.id))

        return assets


def create_virtual_city() -> VirtualCity:
    """
    Create the complete deterministic virtual water system.

    Returns:
        VirtualCity containing:
            - 4 cities
            - 16 zones
            - 108 assets
    """

    # ---------------------------------------------------------
    # 1. Create the four cities
    # ---------------------------------------------------------

    cities = create_cities()

    # ---------------------------------------------------------
    # 2. Create four zones for each city
    # ---------------------------------------------------------

    zones: List[Zone] = []

    for city in cities:

        for zone_number in range(1, 5):

            zone_id = f"{city.id}-Z{zone_number}"

            zone_letter = chr(64 + zone_number)

            zone = Zone(
                id=zone_id,
                name=f"{city.name} Zone {zone_letter}",
                city_id=city.id
            )

            zones.append(zone)

            # Connect the zone to its city.
            city.add_zone_id(zone_id)

    # ---------------------------------------------------------
    # 3. Create assets for each city
    # ---------------------------------------------------------

    assets: List[Asset] = []

    for city in cities:

        city_assets = create_assets_for_city(
            city_id=city.id,
            zone_ids=city.zone_ids,
            treatment_facilities=2,
            reservoirs=2,
            pump_stations=3,
            pipelines=12,
            valves=8
        )

        assets.extend(city_assets)

        # Connect each asset to its zone.
        for asset in city_assets:

            zone = next(
                zone
                for zone in zones
                if zone.id == asset.zone_id
            )

            zone.add_asset_id(asset.id)

    # ---------------------------------------------------------
    # 3b. Populate the global ASSETS registry
    #
    # The same Asset objects are referenced by both
    # VirtualCity.assets and ASSETS. No copies are made.
    #
    # ASSETS.clear() removes any entries left over from a
    # previous call, so repeated calls never produce stale IDs.
    # ---------------------------------------------------------

    ASSETS.clear()

    for asset in assets:
        ASSETS[asset.id] = asset

    # ---------------------------------------------------------
    # 4. Create the complete VirtualCity object
    # ---------------------------------------------------------

    virtual_city = VirtualCity(
        cities=cities,
        zones=zones,
        assets=assets
    )

    # ---------------------------------------------------------
    # 5. Validate the frozen project model
    # ---------------------------------------------------------

    assert len(virtual_city.cities) == 4, \
        "Virtual city must contain 4 cities."

    assert len(virtual_city.zones) == 16, \
        "Virtual city must contain 16 zones."

    assert len(virtual_city.assets) == 108, \
        "Virtual city must contain 108 assets."

    return virtual_city


if __name__ == "__main__":

    virtual_city = create_virtual_city()

    print(f"Cities: {len(virtual_city.cities)}")
    print(f"Zones: {len(virtual_city.zones)}")
    print(f"Assets: {len(virtual_city.assets)}")

    # ---------------------------------------------------------
    # Asset type counts
    # ---------------------------------------------------------

    from collections import Counter

    type_counts = Counter(
        asset.asset_type
        for asset in virtual_city.assets
    )

    print("\nAsset type counts:")

    for asset_type, count in type_counts.items():
        print(f"  {asset_type.value}: {count}")

    # ---------------------------------------------------------
    # Per-city asset counts
    # ---------------------------------------------------------

    print("\nPer-city asset counts:")

    for city in virtual_city.cities:

        city_assets = virtual_city.get_assets_by_city(city.id)

        print(
            f"  {city.name}: "
            f"{len(city_assets)} assets"
        )

    # ---------------------------------------------------------
    # Per-zone asset counts
    # ---------------------------------------------------------

    print("\nPer-zone asset counts:")

    for zone in virtual_city.zones:

        zone_assets = virtual_city.get_assets_by_zone(zone.id)

        print(
            f"  {zone.name}: "
            f"{len(zone_assets)} assets"
        )

    # ---------------------------------------------------------
    # Validate asset → zone relationships
    # ---------------------------------------------------------

    all_zone_ids = {
        zone.id
        for zone in virtual_city.zones
    }

    for asset in virtual_city.assets:

        assert asset.zone_id in all_zone_ids, (
            f"Asset {asset.id} has invalid zone "
            f"{asset.zone_id}"
        )

    # ---------------------------------------------------------
    # Validate zone → city relationships
    # ---------------------------------------------------------

    all_city_ids = {
        city.id
        for city in virtual_city.cities
    }

    for zone in virtual_city.zones:

        assert zone.city_id in all_city_ids, (
            f"Zone {zone.id} has invalid city "
            f"{zone.city_id}"
        )

    # ---------------------------------------------------------
    # Validate unique IDs
    # ---------------------------------------------------------

    asset_ids = [
        asset.id
        for asset in virtual_city.assets
    ]

    zone_ids = [
        zone.id
        for zone in virtual_city.zones
    ]

    city_ids = [
        city.id
        for city in virtual_city.cities
    ]

    assert len(asset_ids) == len(set(asset_ids)), \
        "Duplicate asset IDs found."

    assert len(zone_ids) == len(set(zone_ids)), \
        "Duplicate zone IDs found."

    assert len(city_ids) == len(set(city_ids)), \
        "Duplicate city IDs found."

    # ---------------------------------------------------------
    # Validate ASSETS registry
    # ---------------------------------------------------------

    assert len(ASSETS) == 108, \
        "ASSETS must contain 108 entries."

    for asset in virtual_city.assets:
        assert ASSETS[asset.id] is asset, (
            f"ASSETS[{asset.id}] must reference the same "
            f"Asset object as VirtualCity.assets."
        )

    print("\nAll validations passed.")