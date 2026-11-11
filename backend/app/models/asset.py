"""Asset and infrastructure subtype models.

Base `assets` table plus the five one-to-one subtype tables. Each
subtype uses `asset_id` as both its primary key and a foreign key
into `assets.asset_id`, so IDs are shared, never auto-generated.
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)

from backend.app.database.database import Base


ALLOWED_ASSET_TYPES = (
    "TreatmentFacility",
    "Reservoir",
    "PumpStation",
    "Pipeline",
    "Valve",
)

_ASSET_TYPE_CHECK = (
    "asset_type IN ("
    + ", ".join(f"'{t}'" for t in ALLOWED_ASSET_TYPES)
    + ")"
)


class Asset(Base):
    """Base asset record. All 108 assets have exactly one row here."""

    __tablename__ = "assets"

    asset_id = Column(Integer, primary_key=True)
    zone_id = Column(
        Integer,
        ForeignKey("zones.zone_id"),
        nullable=False,
    )
    parent_asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=True,
    )
    asset_name = Column(String(150), nullable=False)
    asset_type = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(DateTime, nullable=False)

    __table_args__ = (
        CheckConstraint(_ASSET_TYPE_CHECK, name="ck_assets_asset_type"),
        CheckConstraint(
            "parent_asset_id IS NULL OR parent_asset_id <> asset_id",
            name="ck_assets_parent_not_self",
        ),
    )


class TreatmentFacility(Base):
    __tablename__ = "treatment_facilities"

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        primary_key=True,
        autoincrement=False,
    )
    treatment_capacity = Column(Numeric(14, 2), nullable=True)
    treatment_status = Column(String(50), nullable=True)


class Reservoir(Base):
    __tablename__ = "reservoirs"

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        primary_key=True,
        autoincrement=False,
    )
    storage_capacity = Column(Numeric(14, 2), nullable=True)
    current_level = Column(Numeric(12, 3), nullable=True)


class PumpStation(Base):
    __tablename__ = "pump_stations"

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        primary_key=True,
        autoincrement=False,
    )
    pump_count = Column(Integer, nullable=True)
    operational_status = Column(String(50), nullable=True)


class Pipeline(Base):
    __tablename__ = "pipelines"

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        primary_key=True,
        autoincrement=False,
    )
    length = Column(Numeric(12, 2), nullable=True)
    diameter = Column(Numeric(10, 2), nullable=True)
    material = Column(String(50), nullable=True)


class Valve(Base):
    __tablename__ = "valves"

    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        primary_key=True,
        autoincrement=False,
    )
    valve_type = Column(String(50), nullable=True)
    valve_status = Column(String(50), nullable=True)