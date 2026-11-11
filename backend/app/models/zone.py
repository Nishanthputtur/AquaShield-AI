"""Zone model."""

from sqlalchemy import Column, ForeignKey, Integer, String, Text

from backend.app.database.database import Base


class Zone(Base):
    """One zone within a city (16 total)."""

    __tablename__ = "zones"

    zone_id = Column(Integer, primary_key=True)
    zone_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    city_id = Column(
        Integer,
        ForeignKey("cities.city_id"),
        nullable=False,
    )