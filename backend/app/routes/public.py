from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from backend.app.database.database import get_db
from backend.app.models import Complaint, Zone

router = APIRouter(prefix="/api/v1/public", tags=["Public Portal"])

@router.post("/complaints")
def submit_complaint(data: dict, db: Session = Depends(get_db)):
    # Generate a unique tracking ID (e.g., CMP-8F3A2B)
    tracking_id = f"CMP-{str(uuid.uuid4())[:6].upper()}"
    
    new_complaint = Complaint(
        complaint_identification_value=tracking_id,
        zone_id=data.get("zone_id"), # optional
        complaint_details=data.get("details"),
        status="Submitted"
    )
    db.add(new_complaint)
    db.commit()
    
    return {"message": "Complaint submitted", "tracking_id": tracking_id}

@router.get("/complaints/{tracking_id}")
def track_complaint(tracking_id: str, db: Session = Depends(get_db)):
    complaint = db.query(Complaint).filter(Complaint.complaint_identification_value == tracking_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    return {
        "tracking_id": complaint.complaint_identification_value,
        "details": complaint.complaint_details,
        "status": complaint.status,
        "resolution": complaint.resolution_details
    }

@router.get("/zones")
def get_public_zones(db: Session = Depends(get_db)):
    # Helper for the public frontend to get zone IDs
    zones = db.query(Zone).all()
    return [{"zone_id": z.zone_id, "name": z.zone_name} for z in zones]