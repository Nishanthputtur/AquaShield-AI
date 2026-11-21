from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.database.database import get_db
from backend.app.dependencies import require_role
from backend.app.services.analytics_service import run_analytics_for_all
from backend.app.models import AssetHealthScore, RiskScore

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])

@router.post("/process", dependencies=[Depends(require_role("Engineer", "Administrator"))])
def trigger_analytics(db: Session = Depends(get_db)):
    """Run the analytics engine to update anomalies, AHS, and RS."""
    results = run_analytics_for_all(db)
    return {"message": "Analytics processing complete", "count": len(results)}

@router.get("/dashboard", dependencies=[Depends(require_role("Engineer", "Administrator", "Utility Manager"))])
def get_analytics_dashboard(db: Session = Depends(get_db)):
    """Get the latest health and risk scores for the dashboard."""
    # Get the latest score for each asset
    latest_ahs = db.query(AssetHealthScore).order_by(AssetHealthScore.assessment_timestamp.desc()).limit(100).all()
    latest_rs = db.query(RiskScore).order_by(RiskScore.assessment_timestamp.desc()).limit(100).all()
    
    return {
        "ahs_scores": [{"asset_id": a.asset_id, "score": a.score} for a in latest_ahs],
        "rs_scores": [{"asset_id": r.asset_id, "score": r.score} for r in latest_rs]
    }