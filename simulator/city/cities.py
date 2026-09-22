"""
Defines the City dataclass and fictional city data
for the AquaShield AI virtual water city.
"""

from dataclasses import dataclass, field
from typing import List


# Frozen fictional city names for the AquaShield AI model.
CITY_NAMES = [
    "Zorawarpur",
    "Amaranagar",
    "Rajatgiri",
    "Rajatpur",
]


@dataclass
class City:
    """
    Represents a city in the virtual water system.

    Each city contains four zones.
    """

    id: str
    name: str
    zone_ids: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the basic identity information of the city."""

        if not self.id.strip():
            raise ValueError("City ID cannot be empty.")

        if not self.name.strip():
            raise ValueError("City name cannot be empty.")

        if len(set(self.zone_ids)) != len(self.zone_ids):
            raise ValueError("Zone IDs within a city must be unique.")

    def add_zone_id(self, zone_id: str) -> None:
        """
        Add a zone ID to this city.

        Duplicate zone IDs are ignored.
        """

        if not zone_id.strip():
            raise ValueError("Zone ID cannot be empty.")

        if zone_id not in self.zone_ids:
            self.zone_ids.append(zone_id)


def create_cities() -> List[City]:
    """
    Create the four deterministic fictional cities.

    City IDs:
        C1 -> Zorawarpur
        C2 -> Amaranagar
        C3 -> Rajatgiri
        C4 -> Rajatpur

    Zone IDs are assigned later when the zones are created.
    """

    cities: List[City] = []

    for index, name in enumerate(CITY_NAMES, start=1):
        city_id = f"C{index}"

        city = City(
            id=city_id,
            name=name,
        )

        cities.append(city)

    return cities