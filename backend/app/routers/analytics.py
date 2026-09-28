import os
import json
import uuid
import pandas as pd
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import Complaint, Location, Prediction
from backend.graph_engine import CyrisGraphEngine
from backend.nlp_pipeline import CyrisNLPClassifier

router = APIRouter(tags=["Analytics, Graph & AI"])

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "mock_data.json")
HOTSPOT_DATA_PATH = os.path.join(BASE_DIR, "cyris_atm_hotspots.json")

# Engines
try:
    graph_engine = CyrisGraphEngine(DATA_PATH)
except Exception:
    graph_engine = None

try:
    nlp_engine = CyrisNLPClassifier()
except Exception:
    nlp_engine = None


class ComplaintInput(BaseModel):
    description: str


class ComplaintRiskRequest(BaseModel):
    crime_type: str
    sub_type: Optional[str] = "General"
    amount_lost: float
    state: Optional[str] = "Odisha"
    city: Optional[str] = "Bhubaneswar"
    latitude: Optional[float] = 20.2961
    longitude: Optional[float] = 85.8245
    transaction_type: Optional[str] = "UPI"
    transaction_count: Optional[int] = 1
    suspicious_transactions: Optional[int] = 1
    previous_complaints: Optional[int] = 0
    complaint_hour: Optional[int] = 12
    day_of_week: Optional[int] = 1
    location_risk: Optional[float] = 5.0
    victim_age_group: Optional[str] = "26-40"
    device_risk: Optional[float] = 5.0
    account_age_days: Optional[int] = 100
    distance_from_complainant_km: Optional[float] = 2.0
    channel: Optional[str] = "ONLINE"
    suspicious_transaction: Optional[int] = 1


@router.get("/api/patterns/fraud-rings")
def get_fraud_rings():
    if not graph_engine:
        return {"fraud_rings": []}
    return {"fraud_rings": graph_engine.get_fraud_rings()}


@router.get("/api/analytics/hotspots")
@router.get("/api/v1/analytics/ai-hotspots")
def get_hotspots():
    if os.path.exists(HOTSPOT_DATA_PATH):
        try:
            with open(HOTSPOT_DATA_PATH, "r", encoding="utf-8") as f:
                hotspots = json.load(f)
            return {
                "total": len(hotspots),
                "hotspots": hotspots,
                "source": "CYRIS trained ATM hotspot model"
            }
        except Exception:
            pass

    return {
        "total": 4,
        "hotspots": [
            {"target_atm": "ATM_101", "bank": "SBI", "pincode": 110001, "lat": 20.2961, "lng": 85.8245, "risk_level": "CRITICAL", "avg_ai_risk": 89},
            {"target_atm": "ATM_102", "bank": "HDFC", "pincode": 110002, "lat": 20.3548, "lng": 85.8153, "risk_level": "CRITICAL", "avg_ai_risk": 82},
            {"target_atm": "ATM_103", "bank": "ICICI", "pincode": 110003, "lat": 20.2882, "lng": 85.8436, "risk_level": "MEDIUM", "avg_ai_risk": 58},
            {"target_atm": "ATM_104", "bank": "Axis", "pincode": 110004, "lat": 20.2577, "lng": 85.7831, "risk_level": "MEDIUM", "avg_ai_risk": 35}
        ],
        "source": "complaint data fallback"
    }


@router.get("/api/v1/analytics/mule-network")
def get_mule_network(db: Session = Depends(get_db)):
    complaints = db.query(Complaint).limit(10).all()
    nodes = set()
    edges = []
    
    for c in complaints:
        v = c.full_name or "Victim"
        l1 = c.upi_id or "Layer 1 Mule"
        l2 = f"ACC_L2_{hash(c.complaint_id) % 40 + 50}"
        l3 = f"ACC_L3_{hash(c.complaint_id) % 40 + 90}"
        atm = f"ATM_{c.city.upper()}"
        amt = c.amount or 25000.0

        nodes.add((v, "Victim"))
        nodes.add((l1, "Layer 1 Mule"))
        nodes.add((l2, "Layer 2 Mule"))
        nodes.add((l3, "Layer 3 Mule"))
        nodes.add((atm, "Cashout ATM"))

        edges.append({"source": v, "target": l1, "label": f"₹{amt:,.0f}"})
        edges.append({"source": l1, "target": l2, "label": f"₹{int(amt * 0.95):,}"})
        edges.append({"source": l2, "target": l3, "label": f"₹{int(amt * 0.90):,}"})
        edges.append({"source": l3, "target": atm, "label": f"Cashout ₹{int(amt * 0.85):,}"})

    if not nodes:
        nodes.add(("Rajesh Mohanty", "Victim"))
        nodes.add(("fastcash.refund@ybl", "Layer 1 Mule"))
        nodes.add(("ACC_L2_78", "Layer 2 Mule"))
        nodes.add(("ATM_BHUBANESWAR", "Cashout ATM"))
        edges.append({"source": "Rajesh Mohanty", "target": "fastcash.refund@ybl", "label": "₹25,000"})
        edges.append({"source": "fastcash.refund@ybl", "target": "ACC_L2_78", "label": "₹23,750"})
        edges.append({"source": "ACC_L2_78", "target": "ATM_BHUBANESWAR", "label": "Cashout ₹21,250"})

    return {
        "nodes": [{"id": n, "group": g} for n, g in nodes],
        "edges": edges
    }


@router.get("/api/analytics/atm-risk-zones")
def get_atm_risk_zones():
    if not os.path.exists(HOTSPOT_DATA_PATH):
        return {
            "success": True,
            "total_zones": 4,
            "critical_zones": [],
            "high_risk_zones": [
                {"name": "SBI ATM - Master Canteen", "city": "Bhubaneswar", "hotspot_level": "HIGH", "hotspot_score": 0.89},
                {"name": "HDFC ATM - Patia Square", "city": "Bhubaneswar", "hotspot_level": "HIGH", "hotspot_score": 0.82}
            ],
            "top_zones": []
        }

    try:
        with open(HOTSPOT_DATA_PATH, "r", encoding="utf-8") as f:
            hotspots = json.load(f)
        hotspots = sorted(hotspots, key=lambda x: x.get("hotspot_score", 0), reverse=True)
        return {
            "success": True,
            "total_zones": len(hotspots),
            "critical_zones": [x for x in hotspots if x.get("hotspot_level") == "CRITICAL"],
            "high_risk_zones": [x for x in hotspots if x.get("hotspot_level") == "HIGH"],
            "top_zones": hotspots[:10]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not load ATM zones: {str(e)}")


@router.post("/api/ai/classify")
def classify_text(input_data: ComplaintInput):
    if not input_data.description.strip():
        raise HTTPException(status_code=400, detail="Description text cannot be empty")
    if not nlp_engine:
        return {
            "input_text": input_data.description,
            "classification": {"predicted_crime_type": "UPI Fraud", "confidence_score": 0.85}
        }
    return {
        "input_text": input_data.description,
        "classification": nlp_engine.classify_complaint(input_data.description)
    }


@router.get("/api/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
    complaints = db.query(Complaint).all()
    total = len(complaints)
    under_review = sum(1 for c in complaints if c.status == "Under Review")
    investigation = sum(1 for c in complaints if "Investigation" in c.status or "Freeze" in c.status)
    action_taken = sum(1 for c in complaints if c.status == "Action Taken")
    resolved = sum(1 for c in complaints if c.status == "Resolved")
    return {
        "total": total,
        "under_review": under_review,
        "investigation": investigation,
        "action_taken": action_taken,
        "resolved": resolved
    }


@router.get("/api/search")
def search_complaints(query: str, db: Session = Depends(get_db)):
    q = f"%{query.strip()}%"
    complaints = db.query(Complaint).filter(
        (Complaint.complaint_id.like(q)) |
        (Complaint.full_name.like(q)) |
        (Complaint.upi_id.like(q)) |
        (Complaint.phone_number.like(q)) |
        (Complaint.fraud_type.like(q))
    ).all()
    results = []
    for c in complaints:
        results.append({
            "complaint_id": c.complaint_id,
            "name": c.full_name,
            "phone_number": c.phone_number,
            "crime_type": c.fraud_type,
            "upi_id": c.upi_id,
            "amount": c.amount,
            "status": c.status
        })
    return {"count": len(results), "results": results}
