from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models import Alert, Complaint
from backend.app.schemas import AlertResponse, AlertStatusUpdate

router = APIRouter(prefix="/api/alerts", tags=["Alerts System"])

@router.get("", response_model=List[AlertResponse])
def get_alerts(db: Session = Depends(get_db)):
    alerts = db.query(Alert).order_by(Alert.id.desc()).all()
    results = []
    for a in alerts:
        c = db.query(Complaint).filter(Complaint.complaint_id == a.complaint_id).first()
        results.append({
            "id": a.id,
            "complaintId": a.complaint_id,
            "riskScore": a.risk_score,
            "locationName": a.location_name,
            "reason": a.reason,
            "verificationStatus": a.verification_status,
            "timestamp": a.timestamp.isoformat(),
            "fraudType": c.fraud_type if c else "UPI_FRAUD",
            "amount": c.amount if c else 25000.0
        })
    return results

@router.put("/{alert_id}")
def update_alert_status(alert_id: int, data: AlertStatusUpdate, db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert ID not found")
        
    alert.verification_status = data.status
    db.commit()
    
    return {
        "success": True,
        "alertId": alert_id,
        "verificationStatus": data.status,
        "message": f"Alert marked as '{data.status}'"
    }
