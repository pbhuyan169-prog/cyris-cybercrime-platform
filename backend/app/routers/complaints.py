import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Union, Dict, Any

from backend.app.database import get_db
from backend.app.models import Complaint, Prediction, Alert, RelatedCase, InvestigationUpdate, AuditLog
from backend.app.schemas import ComplaintCreate, ComplaintResponse, ComplaintStatusUpdate
from backend.app.security import mask_phone, mask_upi, mask_email
from backend.app.services.ml_service import predict_complaint_risk
from backend.app.websocket_manager import manager

router = APIRouter(prefix="/api/complaints", tags=["Complaints"])

@router.post("", response_model=dict)
async def submit_complaint(
    payload: Union[ComplaintCreate, Dict[str, Any]],
    db: Session = Depends(get_db)
):
    if isinstance(payload, ComplaintCreate):
        data = payload.dict()
    else:
        data = payload

    full_name = data.get("full_name") or data.get("victim_acc") or "Anonymous Victim"
    phone_number = data.get("phone_number") or "+919876543210"
    email = data.get("email")
    fraud_type_raw = data.get("fraud_type") or "UPI_FRAUD"
    fraud_type_str = str(fraud_type_raw).upper().replace(" ", "_")
    transaction_id = data.get("transaction_id") or f"TXN-{uuid.uuid4().hex[:5].upper()}"
    amount = float(data.get("amount") or 0.0)
    upi_id = data.get("upi_id") or data.get("suspect_info")
    city = data.get("city") or "Bhubaneswar"
    state = data.get("state") or "Odisha"
    latitude = float(data.get("latitude") or 20.2961)
    longitude = float(data.get("longitude") or 85.8245)
    description = data.get("description") or f"Incident report logged for {fraud_type_str} involving ₹{amount:,.2f}"

    unique_suffix = str(uuid.uuid4().hex[:4]).upper()
    complaint_id = f"CMP-2026-{unique_suffix}"
    
    # All newly registered user complaints automatically go directly to Cyber Cell
    db_complaint = Complaint(
        complaint_id=complaint_id,
        full_name=full_name,
        phone_number=phone_number,
        email=email,
        fraud_type=fraud_type_str,
        transaction_id=transaction_id,
        amount=amount,
        upi_id=upi_id,
        city=city,
        state=state,
        latitude=latitude,
        longitude=longitude,
        description=description,
        status="Under Cyber Cell Review",
        assigned_authority="CYBER_AUTHORITY",
        bank_request_status="NOT_REQUESTED",
        police_notified=False
    )
    db.add(db_complaint)
    db.commit()
    db.refresh(db_complaint)

    # Execute ML Risk Prediction
    ml_result = predict_complaint_risk(
        fraud_type=fraud_type_str,
        amount=amount
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
    if ml_result["riskScore"] >= 0.70:
        cash_out = ml_result["cashOutLocation"]
        alert_obj = Alert(
            complaint_id=complaint_id,
            risk_score=ml_result["riskScore"],
            location_name=cash_out["locationName"],
            reason=f"High-Risk {fraud_type_str} detected (₹{amount:,.2f})",
            verification_status="Pending"
        )
        db.add(alert_obj)
        
    db.commit()

    # Real-Time WebSocket broadcast payload to Cyber Cell
    websocket_payload = {
        "event": "NEW_COMPLAINT_SUBMITTED",
        "complaintId": complaint_id,
        "fraudType": fraud_type_str,
        "amount": amount,
        "location": {"city": db_complaint.city, "latitude": db_complaint.latitude, "longitude": db_complaint.longitude},
        "riskScore": ml_result["riskScore"],
        "riskLevel": ml_result["riskLevel"],
        "timestamp": db_complaint.created_at.isoformat(),
        "assignedAuthority": "CYBER_AUTHORITY"
    }
    
    await manager.broadcast(websocket_payload)

    return {
        "success": True,
        "status": "success",
        "complaintId": complaint_id,
        "assignedAuthority": "CYBER_AUTHORITY",
        "riskScore": ml_result["riskScore"],
        "riskLevel": ml_result["riskLevel"],
        "cashOutLocation": ml_result["cashOutLocation"],
        "message": "Complaint registered successfully and assigned directly to Cyber Cell."
    }

@router.get("")
def list_complaints(
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    authority_role: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Complaint)
    
    # Persona filtering rules
    if authority_role == "BANK_AUTHORITY":
        # Banker sees ONLY complaints for which Cyber Cell has requested transaction details!
        query = query.filter(Complaint.bank_request_status.in_(["REQUESTED_FROM_BANK", "PROVIDED_BY_BANK"]))
    elif authority_role == "POLICE":
        # Police see ONLY cases analyzed by Cyber Cell and notified to Police!
        query = query.filter((Complaint.police_notified == True) | (Complaint.assigned_authority == "POLICE"))
        
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
            "complaint_id": c.complaint_id,
            "fullName": c.full_name,
            "victim": c.full_name,
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
            "bankRequestStatus": c.bank_request_status or "NOT_REQUESTED",
            "policeNotified": c.police_notified or False,
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
        "bankRequestStatus": c.bank_request_status or "NOT_REQUESTED",
        "policeNotified": c.police_notified or False,
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

@router.post("/{complaint_id}/request-bank-details")
async def request_bank_details(complaint_id: str, db: Session = Depends(get_db)):
    """Cyber Cell requests transaction details from the Bank for this specific complaint."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    c.bank_request_status = "REQUESTED_FROM_BANK"
    c.status = "Bank Info Requested"
    db.commit()
    
    await manager.broadcast({
        "event": "BANK_DETAILS_REQUESTED",
        "complaintId": complaint_id,
        "transactionId": c.transaction_id,
        "amount": c.amount,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "success": True,
        "complaintId": complaint_id,
        "bankRequestStatus": "REQUESTED_FROM_BANK",
        "message": f"Transaction details request sent to Bank for Complaint {complaint_id}."
    }

@router.post("/{complaint_id}/provide-bank-details")
async def provide_bank_details(complaint_id: str, db: Session = Depends(get_db)):
    """Banker approves and provides transaction details to Cyber Cell for this requested complaint."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    c.bank_request_status = "PROVIDED_BY_BANK"
    c.status = "Bank Details Provided"
    db.commit()
    
    await manager.broadcast({
        "event": "BANK_DETAILS_PROVIDED",
        "complaintId": complaint_id,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "success": True,
        "complaintId": complaint_id,
        "bankRequestStatus": "PROVIDED_BY_BANK",
        "message": f"Transaction details for Complaint {complaint_id} provided by Bank to Cyber Cell."
    }

@router.post("/{complaint_id}/notify-police")
async def notify_police(complaint_id: str, db: Session = Depends(get_db)):
    """Cyber Cell analyzes the complaint with AI and notifies/dispatches the details to Police."""
    c = db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Complaint not found")
        
    c.police_notified = True
    c.assigned_authority = "POLICE"
    c.status = "Notified to Police"
    db.commit()
    
    await manager.broadcast({
        "event": "NOTIFIED_TO_POLICE",
        "complaintId": complaint_id,
        "fraudType": c.fraud_type,
        "amount": c.amount,
        "city": c.city,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return {
        "success": True,
        "complaintId": complaint_id,
        "policeNotified": True,
        "status": "Notified to Police",
        "message": f"Complaint {complaint_id} analyzed by AI and dispatched to Police."
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
    
    await manager.broadcast({
        "event": "STATUS_UPDATED",
        "complaintId": complaint_id,
        "oldStatus": old_status,
        "newStatus": data.status,
        "timestamp": datetime.utcnow().isoformat()
    })

    return {"success": True, "complaintId": complaint_id, "status": data.status}
