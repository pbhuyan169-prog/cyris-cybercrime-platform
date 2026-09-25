from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import Prediction, Complaint
from backend.app.schemas import PredictionRequest, PredictionResponse, PredictionVerification
from backend.app.services.ml_service import predict_complaint_risk
from backend.app.websocket_manager import manager

router = APIRouter(prefix="/api/predictions", tags=["Predictions & AI"])

@router.post("", response_model=PredictionResponse)
def trigger_prediction(data: PredictionRequest):
    res = predict_complaint_risk(
        fraud_type=data.fraudType,
        amount=data.amount,
        hour_of_day=data.hourOfDay or 14,
        victim_age_group=data.victimAgeGroup or "26-40",
        device_risk=data.deviceRisk or 5.0,
        location_risk=data.locationRisk or 6.0,
        previous_complaints=data.previousComplaints or 0
    )
    
    return PredictionResponse(
        complaintId="DEMO-CMP-PRED",
        riskScore=res["riskScore"],
        riskLevel=res["riskLevel"],
        confidence=res["confidence"],
        predictionStatus="Pending Verification",
        cashOutLocation=res["cashOutLocation"]
    )

@router.post("/{complaint_id}/verify")
async def verify_prediction(
    complaint_id: str,
    data: PredictionVerification,
    db: Session = Depends(get_db)
):
    pred = db.query(Prediction).filter(Prediction.complaint_id == complaint_id).order_by(Prediction.id.desc()).first()
    if not pred:
        # Create prediction record if missing
        pred = Prediction(
            complaint_id=complaint_id,
            risk_score=0.87,
            risk_level="HIGH",
            confidence=0.89,
            status=data.status
        )
        db.add(pred)
    else:
        pred.status = data.status
        
    db.commit()
    
    # Broadcast verification update live via WebSockets
    await manager.broadcast({
        "event": "PREDICTION_VERIFIED",
        "complaintId": complaint_id,
        "verificationStatus": data.status,
        "notes": data.notes or "Prediction status updated by authority"
    })

    return {
        "success": True,
        "complaintId": complaint_id,
        "verificationStatus": data.status,
        "message": f"AI Risk Prediction marked as '{data.status}' by investigator."
    }
