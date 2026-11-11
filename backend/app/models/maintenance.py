"""Health, risk, inspection, and maintenance models."""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)

from backend.app.database.database import Base


class AssetHealthScore(Base):
    """One AHS assessment for one asset. Score 0–100."""

    __tablename__ = "asset_health_scores"

    ahs_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    score = Column(Numeric(5, 2), nullable=False)
    assessment_timestamp = Column(DateTime, nullable=False)
    explanation = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_ahs_score_range",
        ),
    )


class RiskScore(Base):
    """One risk assessment for one asset. Score 0–100."""

    __tablename__ = "risk_scores"

    risk_score_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    score = Column(Numeric(5, 2), nullable=False)
    assessment_timestamp = Column(DateTime, nullable=False)
    explanation = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_risk_score_range",
        ),
    )


class Inspection(Base):
    """One inspection of one asset by one Field Inspector user."""

    __tablename__ = "inspections"

    inspection_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    inspector_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    inspection_date = Column(DateTime, nullable=False)
    findings = Column(Text, nullable=False)
    condition = Column(String(50), nullable=True)
    status = Column(String(30), nullable=True)


class MaintenanceRecord(Base):
    """One maintenance action on one asset by one Maintenance Officer."""

    __tablename__ = "maintenance_records"

    maintenance_id = Column(Integer, primary_key=True)
    asset_id = Column(
        Integer,
        ForeignKey("assets.asset_id"),
        nullable=False,
    )
    maintenance_officer_id = Column(
        Integer,
        ForeignKey("users.user_id"),
        nullable=False,
    )
    maintenance_date = Column(DateTime, nullable=False)
    maintenance_details = Column(Text, nullable=False)
    status = Column(String(30), nullable=False)
    notes = Column(Text, nullable=True)