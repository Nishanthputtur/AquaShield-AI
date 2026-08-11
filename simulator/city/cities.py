"""
City definitions for the water distribution simulation.
Contains the 4 cities with their IDs and names.
"""

from enum import Enum
from typing import Dict, List


class CityID(str, Enum):
    """City identifiers."""

    ZORAWARPUR = "ZORAWARPUR"
    AMARANAGAR = "AMARANAGAR"
    RAJATGIRI = "RAJATGIRI"
    RAJATPUR = "RAJATPUR"


class City:
    """Represents a city in the simulation."""

    def __init__(self, city_id: str, name: str, zone_ids: List[str]):
        self.city_id = city_id
        self.name = name
        self.zone_ids = zone_ids
        self.zones = {}

    def __repr__(self) -> str:
        return f"City({self.city_id}, {self.name}, zones={len(self.zone_ids)})"


# Frozen city configuration

CITY_CONFIG = {
    CityID.ZORAWARPUR: {
        "name": "Zorawarpur",
        "zones": ["Z-01", "Z-02", "Z-03", "Z-04"]
    },
    CityID.AMARANAGAR: {
        "name": "Amaranagar",
        "zones": ["Z-05", "Z-06", "Z-07", "Z-08"]
    },
    CityID.RAJATGIRI: {
        "name": "Rajatgiri",
        "zones": ["Z-09", "Z-10", "Z-11", "Z-12"]
    },
    CityID.RAJATPUR: {
        "name": "Rajatpur",
        "zones": ["Z-13", "Z-14", "Z-15", "Z-16"]
    }
}


def create_cities() -> Dict[str, City]:
    cities = {}

    for city_id, config in CITY_CONFIG.items():
        city = City(
            city_id=city_id.value,
            name=config["name"],
            zone_ids=config["zones"]
        )

        cities[city_id.value] = city

    return cities


# Global city registry

CITIES = create_cities()