"""Complaint and notification models."""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    text,
)

from backend.app.database.database import Base


class Complaint(Base):
    """Public complaint. `complaint_identification_value` is the
    publicly trackable identifier — distinct from the integer PK."""

    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True)
    complaint_identification_value = Column(
        String(100),
        nullable=False,
        unique=True,
    )
    zone_id = Column(
        Integer,
        ForeignKey("zones.zone_id"),
        nullable=True,
    )
    complaint_details = Column(Text, nullable=False)
    submitted_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    status = Column(String(30), nullable=False)
    resolution_details = Column(Text, nullable=True)


class Notification(Base):
    """Notification. NULL `complaint_id` means a general public update."""

    __tablename__ = "notifications"

    notification_id = Column(Integer, primary_key=True)
    complaint_id = Column(
        Integer,
        ForeignKey("complaints.complaint_id"),
        nullable=True,
    )
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)
    created_at = Column(
        DateTime,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )