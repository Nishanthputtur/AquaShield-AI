from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.database.database import get_db
from backend.app.dependencies import require_role
from backend.app.models.maintenance import AssetHealthScore, RiskScore
from backend.app.schemas.analytics import AnalyticsDashboardResponse, AnalyticsProcessResponse
from backend.app.services.analytics_service import run_analytics_for_all

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.post(
    "/process",
    response_model=AnalyticsProcessResponse,
    dependencies=[Depends(require_role("Engineer"))],
)
def trigger_analytics(db: Session = Depends(get_db)):
    """Run decision intelligence. Engineer access only."""

    result = run_analytics_for_all(db)

    return {
        "message": "Analytics processing complete",
        "count": result["assets_processed"],
        **result,
    }


@router.get(
    "/dashboard",
    response_model=AnalyticsDashboardResponse,
    dependencies=[
        Depends(require_role("Engineer", "Maintenance Officer", "Utility Manager"))
    ],
)
def get_analytics_dashboard(db: Session = Depends(get_db)):
    """Get the latest health and risk scores per asset for the dashboard.
    
    Review analytical results (Engineer, Maintenance Officer, Utility Manager per Detailed Design 5.2).
    """
    # Latest AHS per asset by assessment time, then record ID.
    sub_ahs = (
        db.query(
            AssetHealthScore.ahs_id.label("score_id"),
            func.row_number().over(
                partition_by=AssetHealthScore.asset_id,
                order_by=(
                    AssetHealthScore.assessment_timestamp.desc(),
                    AssetHealthScore.ahs_id.desc(),
                ),
            ).label("row_number"),
        )
        .subquery()
    )
    latest_ahs = (
        db.query(AssetHealthScore)
        .join(sub_ahs, AssetHealthScore.ahs_id == sub_ahs.c.score_id)
        .filter(sub_ahs.c.row_number == 1)
        .order_by(AssetHealthScore.score.desc(), AssetHealthScore.asset_id.asc())
        .all()
    )

    # Latest RS per asset by assessment time, then record ID.
    sub_rs = (
        db.query(
            RiskScore.risk_score_id.label("score_id"),
            func.row_number().over(
                partition_by=RiskScore.asset_id,
                order_by=(
                    RiskScore.assessment_timestamp.desc(),
                    RiskScore.risk_score_id.desc(),
                ),
            ).label("row_number"),
        )
        .subquery()
    )
    latest_rs = (
        db.query(RiskScore)
        .join(sub_rs, RiskScore.risk_score_id == sub_rs.c.score_id)
        .filter(sub_rs.c.row_number == 1)
        .order_by(RiskScore.score.desc(), RiskScore.asset_id.asc())
        .all()
    )

    ahs_items = [{"asset_id": a.asset_id, "score": float(a.score)} for a in latest_ahs]
    rs_items = [{"asset_id": r.asset_id, "score": float(r.score)} for r in latest_rs]

    return {
        "ahs": ahs_items,
        "rs": rs_items,
        "ahs_scores": ahs_items,
        "rs_scores": rs_items,
    }
