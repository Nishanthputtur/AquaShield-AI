"""
Zone definitions for the water distribution simulation.
Contains the 16 zones with exact frozen names.
"""

from typing import Dict, List


class Zone:
    """Represents a zone within a city."""

    def __init__(self, zone_id: str, name: str, city_id: str):
        self.zone_id = zone_id
        self.name = name
        self.city_id = city_id
        self.assets = {}
        self.sensors = {}

    def __repr__(self) -> str:
        return f"Zone({self.zone_id}, {self.name}, city={self.city_id})"


# Frozen zone configuration
# Exact names from the finalized specification

ZONE_CONFIG = {
    # Zorawarpur
    "Z-01": {"name": "North Heights", "city": "ZORAWARPUR"},
    "Z-02": {"name": "Central Zora", "city": "ZORAWARPUR"},
    "Z-03": {"name": "Zora Industrial Belt", "city": "ZORAWARPUR"},
    "Z-04": {"name": "New Zora", "city": "ZORAWARPUR"},

    # Amaranagar
    "Z-05": {"name": "Amara Central", "city": "AMARANAGAR"},
    "Z-06": {"name": "Corporate Park", "city": "AMARANAGAR"},
    "Z-07": {"name": "Executive Enclave", "city": "AMARANAGAR"},
    "Z-08": {"name": "Eastern Expansion", "city": "AMARANAGAR"},

    # Rajatgiri
    "Z-09": {"name": "Rajat Heights", "city": "RAJATGIRI"},
    "Z-10": {"name": "Financial District", "city": "RAJATGIRI"},
    "Z-11": {"name": "Valley Quarter", "city": "RAJATGIRI"},
    "Z-12": {"name": "Mountain Edge", "city": "RAJATGIRI"},

    # Rajatpur
    "Z-13": {"name": "Rajat Central", "city": "RAJATPUR"},
    "Z-14": {"name": "Coastal Front", "city": "RAJATPUR"},
    "Z-15": {"name": "Port District", "city": "RAJATPUR"},
    "Z-16": {"name": "South Marina", "city": "RAJATPUR"}
}


def create_zones() -> Dict[str, Zone]:
    zones = {}

    for zone_id, config in ZONE_CONFIG.items():
        zone = Zone(
            zone_id=zone_id,
            name=config["name"],
            city_id=config["city"]
        )

        zones[zone_id] = zone

    return zones


# Global zone registry

ZONES = create_zones()


def get_zones_by_city(city_id: str) -> List[Zone]:
    return [
        zone
        for zone in ZONES.values()
        if zone.city_id == city_id
    ]