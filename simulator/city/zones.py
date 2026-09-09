"""
Defines the Zone dataclass for the AquaShield AI virtual water city.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Zone:
    """
    Represents a zone within a virtual water city.

    A zone belongs to one city and maintains the IDs
    of the assets located within that zone.
    """

    id: str
    name: str
    city_id: str
    asset_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the basic identity information of the zone."""

        if not self.id.strip():
            raise ValueError("Zone ID cannot be empty.")

        if not self.name.strip():
            raise ValueError("Zone name cannot be empty.")

        if not self.city_id.strip():
            raise ValueError("City ID cannot be empty.")

        if len(set(self.asset_ids)) != len(self.asset_ids):
            raise ValueError("Asset IDs within a zone must be unique.")

    def add_asset_id(self, asset_id: str) -> None:
        """
        Add an asset ID to this zone.

        Duplicate asset IDs are ignored.
        """

        if not asset_id.strip():
            raise ValueError("Asset ID cannot be empty.")

        if asset_id not in self.asset_ids:
            self.asset_ids.append(asset_id)

    def remove_asset_id(self, asset_id: str) -> None:
        """
        Remove an asset ID from this zone.

        Does nothing if the asset ID is not present.
        """

        if asset_id in self.asset_ids:
            self.asset_ids.remove(asset_id)