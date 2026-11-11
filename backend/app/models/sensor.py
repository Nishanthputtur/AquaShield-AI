"""Sensor, reading, and anomaly models."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)

from backend.app.database.database import Base


ALLOWED_SENSOR_TYPES = (
    "Flow",
    "Pressure",
    "Level",
    "Water Temperature",
    "pH",
    "Turbidity",
    "Equipment Condition",
)

_SENSOR_TYPE_CHECK = (
    "sensor_type IN ("
    + ", ".join(f"'{t}'" for t in ALLOWED_SENSOR_TYPES)
    + ")"
)


class Sensor(Base):
    """Virtual sensor. Exactly 328 rows after seeding."""

    __tablename__ = "sensors"

    sensor_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    sensor_type = Column(String(30), nullable=False)
    sensor_name = Column(String(100), nullable=False)
    status = Column(String(30), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    __table_args__ = (
        CheckConstraint(_SENSOR_TYPE_CHECK, name="ck_sensors_sensor_type"),
    )


class SensorReading(Base):
    """One reading from one sensor.

    Exactly one of `reading_value_numeric` and `reading_value_text` is
    non-null, enforced by a table-level CHECK constraint.
    """

    __tablename__ = "sensor_readings"

    reading_id = Column(Integer, primary_key=True)
    sensor_id = Column(
        Integer,
        ForeignKey("sensors.sensor_id"),
        nullable=False,
    )
    reading_value_numeric = Column(Numeric(14, 4), nullable=True)
    reading_value_text = Column(Text, nullable=True)
    # Column literally named `timestamp`, per the design spec.
    timestamp = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "(reading_value_numeric IS NOT NULL AND reading_value_text IS NULL) "
            "OR (reading_value_numeric IS NULL AND reading_value_text IS NOT NULL)",
            name="ck_sensor_readings_value_exclusive",
        ),
    )


class Anomaly(Base):
    """Detected anomaly. `sensor_reading_id` may be NULL.

    When set, application-level validation must confirm the reading's
    sensor belongs to the anomaly's `asset_id`.
    """

    __tablename__ = "anomalies"

    anomaly_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    sensor_reading_id = Column(
        Integer,
        ForeignKey("sensor_readings.reading_id"),
        nullable=True,
    )
    anomaly_type = Column(String(80), nullable=False)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime, nullable=False)
    status = Column(String(30), nullable=True)