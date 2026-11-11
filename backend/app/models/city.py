"""City model."""

from sqlalchemy import Column, Integer, String, Text

from backend.app.database.database import Base


class City(Base):
    """One virtual city (4 total)."""

    __tablename__ = "cities"

    city_id = Column(Integer, primary_key=True)
    city_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)