from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from backend.app.database import get_db
from backend.app.models import Location
from backend.app.schemas import RiskLocationResponse

router = APIRouter(prefix="/api/risk-locations", tags=["GIS Analytics"])

@router.get("", response_model=List[RiskLocationResponse])
def get_risk_locations(db: Session = Depends(get_db)):
    locations = db.query(Location).all()
    if not locations:
        # Fallback dataset if empty DB
        return [
            {
                "id": 1,
                "name": "SBI ATM - Master Canteen",
                "city": "Bhubaneswar",
                "state": "Odisha",
                "latitude": 20.2961,
                "longitude": 85.8245,
                "riskLevel": "HIGH",
                "relatedCasesCount": 8,
                "suspiciousTxCount": 18,
                "riskScore": 0.89,
                "lastTxTime": "10 mins ago"
            },
            {
                "id": 2,
                "name": "HDFC ATM - Patia Square",
                "city": "Bhubaneswar",
                "state": "Odisha",
                "latitude": 20.3548,
                "longitude": 85.8153,
                "riskLevel": "HIGH",
                "relatedCasesCount": 5,
                "suspiciousTxCount": 12,
                "riskScore": 0.82,
                "lastTxTime": "25 mins ago"
            },
            {
                "id": 3,
                "name": "ICICI ATM - Saheed Nagar",
                "city": "Bhubaneswar",
                "state": "Odisha",
                "latitude": 20.2882,
                "longitude": 85.8436,
                "riskLevel": "MEDIUM",
                "relatedCasesCount": 3,
                "suspiciousTxCount": 6,
                "riskScore": 0.58,
                "lastTxTime": "1 hour ago"
            },
            {
                "id": 4,
                "name": "Axis Bank ATM - Khandagiri",
                "city": "Bhubaneswar",
                "state": "Odisha",
                "latitude": 20.2577,
                "longitude": 85.7831,
                "riskLevel": "LOW",
                "relatedCasesCount": 1,
                "suspiciousTxCount": 2,
                "riskScore": 0.28,
                "lastTxTime": "3 hours ago"
            }
        ]

    res = []
    for loc in locations:
        score_val = 0.89 if loc.risk_level == "HIGH" or loc.risk_level == "CRITICAL" else (0.58 if loc.risk_level == "MEDIUM" else 0.28)
        res.append({
            "id": loc.id,
            "name": loc.name,
            "city": loc.city,
            "state": loc.state,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "riskLevel": loc.risk_level,
            "relatedCasesCount": loc.related_cases_count,
            "suspiciousTxCount": loc.suspicious_tx_count,
            "riskScore": score_val,
            "lastTxTime": loc.last_tx_time or "Recently"
        })
    return res
