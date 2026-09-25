import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from backend.app.database import get_db
from backend.app.models import Complaint, Prediction, Alert, RelatedCase, InvestigationUpdate, AuditLog
from backend.app.schemas import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate
from backend.app.security import mask_phone, mask_upi, mask_email
from backend.app.services.ml_service import predict_complaint_risk
from backend.app.websocket_manager import manager

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

@router.post("", response_model=dict)
async def submit_complaint(
    complaint: ComplaintCreate,
    db: Session = Depends(get_db)
):
    # Generate unique complaint ID
    unique_suffix = str(uuid.uuid4().hex[:4]).upper()
    complaint_id = f"CMP-2026-{unique_suffix}"
    
    # Standardize fraud type
    fraud_type_str = complaint.fraud_type.upper().replace(" ", "_")
    
    db_complaint = Complaint(
        complaint_id=complaint_id,
        full_name=complaint.full_name,
        phone_number=complaint.phone_number,
        email=complaint.email,
        fraud_type=fraud_type_str,
        transaction_id=complaint.transaction_id or f"TXN-{uuid.uuid4().hex[:5].upper()}",
        amount=complaint.amount,
        upi_id=complaint.upi_id,
        city=complaint.city or "Bhubaneswar",
        state=complaint.state or "Odisha",
        latitude=complaint.latitude or 20.2961,
        longitude=complaint.longitude or 85.8245,
        description=complaint.description,
        status="Under Review",
        assigned_authority="CYBER_AUTHORITY" # Automatically routes to Cyber Authority
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)

    # Execute ML Risk Prediction
    ml_result = predict_complaint_risk(
        fraud_type=fraud_type_str,
        amount=complaint.amount
    )
    
    # Save Prediction to DB
    pred_obj = Prediction(
        complaint_id=complaint_id,
        risk_score=ml_result["riskScore"],
        risk_level=ml_result["riskLevel"],
        confidence=ml_result["confidence"],
        status="Pending Verification"
    )
    db.add(pred_obj)

    # Check alert threshold
    alert_created = False
    if ml_result["riskScore"] >= 0.70:
        alert_created = True
        cash_out = ml_result["cashOutLocation"]
        alert_obj = Alert(
            complaint_id=complaint_id,
            risk_score=ml_result["riskScore"],
            location_name=cash_out["locationName"],
            reason=f"High-Risk {fraud_type_str} detected (₹{complaint.amount:,.2f})",
            verification_status="Pending"
        )
        db.add(alert_obj)
        
    db.commit()

    # Real-Time WebSocket broadcast payload to all authority clients
    websocket_payload = {
        "event": "NEW_COMPLAINT_SUBMITTED",
        "complaintId": complaint_id,
        "fraudType": fraud_type_str,
        "amount": complaint.amount,
        "location": {"city": db_complaint.city, "latitude": db_complaint.latitude, "longitude": db_complaint.longitude},
        "riskScore": ml_result["riskScore"],
        "riskLevel": ml_result["riskLevel"],
        "timestamp": db_complaint.created_at.isoformat(),
        "assignedAuthority": "CYBER_AUTHORITY"
    }
    
    await manager.broadcast(websocket_payload)

    return {
        "success": True,
        "complaintId": complaint_id,
        "status": "Under Review",
        "assignedAuthority": "CYBER_AUTHORITY",
        "riskScore": ml_result["riskScore"],
        "riskLevel": ml_result["riskLevel"],
        "cashOutLocation": ml_result["cashOutLocation"],
        "message": "Complaint successfully registered and routed to Cyber Authority."
    }

@router.get("")
def list_complaints(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Complaint)
    
    if search:
        s = f"%{search.strip()}%"
        query = query.filter(
            (Complaint.complaint_id.like(s)) |
            (Complaint.full_name.like(s)) |
            (Complaint.upi_id.like(s)) |
            (Complaint.phone_number.like(s))
        )
        
    if status and status != "ALL":
        query = query.filter(Complaint.status == status)
        
    complaints = query.order_by(Complaint.id.desc()).all()
    
    results = []
    for c in complaints:
        latest_pred = db.query(Prediction).filter(Prediction.complaint_id == c.complaint_id).order_by(Prediction.id.desc()).first()
        results.append({
            "complaintId": c.complaint_id,
            "fullName": c.full_name,
            "phoneNumberMasked": mask_phone(c.phone_number),
            "emailMasked": mask_email(c.email) if c.email else None,
            "fraudType": c.fraud_type,
            "transactionId": c.transaction_id,
            "amount": c.amount,
            "upiIdMasked": mask_upi(c.upi_id) if c.upi_id else None,
            "city": c.city,
            "state": c.state,
            "location": {"latitude": c.latitude, "longitude": c.longitude},
            "description": c.description,
            "status": c.status,
            "assignedAuthority": c.assigned_authority,
            "timestamp": c.created_at.isoformat(),
            "riskScore": latest_pred.risk_score if latest_pred else 0.50,
            "riskLevel": latest_pred.risk_level if latest_pred else "MEDIUM"
        })
        
    return results

@router.get("/{complaint_id}")
def get_complaint_by_id(complaint_id: str, db: Session = Depends(get_db)):
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint ID not found")
        
    pred = db.query(Prediction).filter(Prediction.complaint_id == complaint_id).order_by(Prediction.id.desc()).first()
    alerts = db.query(Alert).filter(Alert.complaint_id == complaint_id).all()
    
    # Related cases simulation
    related = db.query(RelatedCase).filter(
        (RelatedCase.complaint_id_1 == complaint_id) | (RelatedCase.complaint_id_2 == complaint_id)
    ).all()
    
    related_list = []
    for r in related:
        other_id = r.complaint_id_2 if r.complaint_id_1 == complaint_id else r.complaint_id_1
        related_list.append({
            "complaintId": other_id,
            "similarityReason": r.similarity_reason,
            "similarityScore": r.similarity_score
        })

    return {
        "complaintId": c.complaint_id,
        "fullName": c.full_name,
        "phoneNumberMasked": mask_phone(c.phone_number),
        "emailMasked": mask_email(c.email) if c.email else None,
        "fraudType": c.fraud_type,
        "transactionId": c.transaction_id,
        "amount": c.amount,
        "upiIdMasked": mask_upi(c.upi_id) if c.upi_id else None,
        "city": c.city,
        "state": c.state,
        "location": {"latitude": c.latitude, "longitude": c.longitude},
        "description": c.description,
        "status": c.status,
        "assignedAuthority": c.assigned_authority,
        "timestamp": c.created_at.isoformat(),
        "prediction": {
            "riskScore": pred.risk_score if pred else 0.50,
            "riskLevel": pred.risk_level if pred else "MEDIUM",
            "confidence": pred.confidence if pred else 0.85,
            "status": pred.status if pred else "Pending Verification"
        },
        "relatedCases": related_list,
        "alertsCount": len(alerts)
    }

@router.put("/{complaint_id}/status")
async def update_complaint_status(
    complaint_id: str,
    data: ComplaintStatusUpdate,
    db: Session = Depends(get_db)
):
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    old_status = c.status
    c.status = data.status
    
    log = InvestigationUpdate(
        complaint_id=complaint_id,
        authority_user="Investigator",
        authority_role="AUTHORITY",
        status_from=old_status,
        status_to=data.status,
        notes=data.notes or "Status updated by authority user"
    )
    db.add(log)
    db.commit()
    
    # Broadcast real-time status update via WebSocket
    await manager.broadcast({
        "event": "STATUS_UPDATED",
        "complaintId": complaint_id,
        "oldStatus": old_status,
        "newStatus": data.status,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"success": True, "complaintId": complaint_id, "status": data.status}
