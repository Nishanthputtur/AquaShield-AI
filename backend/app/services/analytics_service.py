from sqlalchemy.orm import Session
from backend.app.models import (
    Asset, Anomaly, AssetHealthScore, RiskScore, 
    Sensor, SensorReading, MaintenanceRecord
)
from datetime import datetime

def run_analytics_for_all(db: Session):
    """Processes all assets to calculate Anomalies, AHS, and RS."""
    assets = db.query(Asset).all()
    results = []
    
    for asset in assets:
        # 1. Fetch the sensors for this asset from the DB
        asset_sensors = db.query(Sensor).filter(Sensor.asset_id == asset.asset_id).all()
        sensor_ids = [s.sensor_id for s in asset_sensors]
        
        # Create a lookup map: { sensor_id: "Pressure" or "Flow" }
        sensor_type_map = {s.sensor_id: s.sensor_type for s in asset_sensors}
        
        # 2. Simple Rule-Based Anomaly Detection
        recent_readings = []
        if sensor_ids:
            recent_readings = db.query(SensorReading).filter(
                SensorReading.sensor_id.in_(sensor_ids)
            ).order_by(SensorReading.timestamp.desc()).limit(5).all()
        
        anomaly_detected = False
        anomaly_reason = ""
        
        for r in recent_readings:
            if r.reading_value_numeric is not None:
                # Look up the actual string type of this sensor
                s_type = sensor_type_map.get(r.sensor_id, "")
                
                # Rule: Pressure < 30 PSI is an anomaly
                if "Pressure" in s_type and r.reading_value_numeric < 30:
                    anomaly_detected = True
                    anomaly_reason = "Low Pressure"
                # Rule: Flow < 50 L/min is an anomaly
                elif "Flow" in s_type and r.reading_value_numeric < 50:
                    anomaly_detected = True
                    anomaly_reason = "Low Flow"
        
        # Save anomaly if detected
        if anomaly_detected:
            new_anomaly = Anomaly(
                asset_id=asset.asset_id,
                anomaly_type="Operational",
                description=f"Rule triggered: {anomaly_reason}",
                detected_at=datetime.now(),
                status="Detected"
            )
            db.add(new_anomaly)

        # 3. Calculate Asset Health Score (AHS) - 0 to 100 (100 is best)
        anomaly_count = db.query(Anomaly).filter(Anomaly.asset_id == asset.asset_id).count()
        maint_count = db.query(MaintenanceRecord).filter(MaintenanceRecord.asset_id == asset.asset_id).count()
        
        ahs_score = max(0.0, 100.0 - (anomaly_count * 5) - (maint_count * 2))
        
        new_ahs = AssetHealthScore(
            asset_id=asset.asset_id,
            score=ahs_score,
            assessment_timestamp=datetime.now(),
            explanation=f"Base 100 - {anomaly_count} anomalies (-5) - {maint_count} maintenance (-2)"
        )
        db.add(new_ahs)

        # 4. Calculate Risk Score (RS) - 0 to 100 (100 is worst)
        multiplier = 1.5 if asset.asset_type == "TreatmentFacility" else 1.0
        rs_score = min(100.0, (100.0 - ahs_score) * multiplier)
        
        new_rs = RiskScore(
            asset_id=asset.asset_id,
            score=rs_score,
            assessment_timestamp=datetime.now(),
            explanation=f"Inverse of AHS ({ahs_score}) x {multiplier} multiplier"
        )
        db.add(new_rs)

        results.append({"asset_id": asset.asset_id, "ahs": ahs_score, "rs": rs_score})

    db.commit()
    return results