"""
Analytics response schemas for AquaShield AI.
"""

from typing import List

from pydantic import BaseModel, ConfigDict


class ScoreItem(BaseModel):
    """Score for one infrastructure asset."""

    model_config = ConfigDict(from_attributes=True)

    asset_id: int
    score: float


class AssetDecisionItem(BaseModel):
    """Internal decision-support output for one asset."""

    asset_id: int
    asset_type: str
    ahs: float
    rs: float
    anomaly_count: int
    maintenance_priority: float
    recommendation: str


class AnalyticsDashboardResponse(BaseModel):
    """Latest health and risk scores per asset."""

    ahs: List[ScoreItem]
    rs: List[ScoreItem]
    ahs_scores: List[ScoreItem]
    rs_scores: List[ScoreItem]


class AnalyticsProcessResponse(BaseModel):
    """Summary and decision outputs from one analytics run."""

    message: str
    count: int
    total_anomalies: int
    assets_processed: int
    asset_decisions: List[AssetDecisionItem]
    maintenance_queue: List[AssetDecisionItem]