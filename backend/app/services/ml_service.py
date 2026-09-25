import os
import joblib
import pandas as pd
from backend.app.config import settings

_model = None

def load_ml_model():
    global _model
    if _model is not None:
        return _model

    model_path = settings.MODEL_PATH
    if not os.path.exists(model_path):
        # Auto-train if missing
        try:
            from backend.ml.train_model import train_and_save_model
            model_path = train_and_save_model()
        except Exception as e:
            print(f"Warning: Failed to train ML model: {e}")
            return None

    try:
        _model = joblib.load(model_path)
        print("OK: Cybercrime Risk Model loaded successfully.")
        return _model
    except Exception as e:
        print(f"Warning: Could not load ML model from {model_path}: {e}. Retraining model...")
        try:
            from backend.ml.train_model import train_and_save_model
            model_path = train_and_save_model()
            _model = joblib.load(model_path)
            print("OK: Cybercrime Risk Model retrained and loaded successfully.")
            return _model
        except Exception as err:
            print(f"Warning: Failed to retrain ML model: {err}")
            return None


def predict_complaint_risk(
    fraud_type: str,
    amount: float,
    hour_of_day: int = 14,
    victim_age_group: str = "26-40",
    device_risk: float = 5.0,
    location_risk: float = 6.0,
    previous_complaints: int = 0
) -> dict:
    
    # 1. Calculation heuristic fallback / confidence score
    raw_score = 0.20 # baseline
    if amount >= 25000:
        raw_score += 0.35
    elif amount >= 10000:
        raw_score += 0.20
    elif amount >= 5000:
        raw_score += 0.10

    if fraud_type.upper() in ["UPI_FRAUD", "UPI FRAUD", "ATM_FRAUD", "ATM FRAUD", "BANKING_FRAUD"]:
        raw_score += 0.25

    if hour_of_day in [23, 0, 1, 2, 3, 4]:
        raw_score += 0.15

    if previous_complaints > 0:
        raw_score += 0.10

    risk_score = round(min(0.98, max(0.12, raw_score)), 2)

    model = load_ml_model()
    risk_level = "MEDIUM"
    confidence = 0.85

    if model is not None:
        try:
            input_df = pd.DataFrame([{
                "fraud_type": fraud_type.upper().replace(" ", "_"),
                "amount": float(amount),
                "hour_of_day": int(hour_of_day),
                "victim_age_group": victim_age_group,
                "device_risk": float(device_risk),
                "location_risk": float(location_risk),
                "previous_complaints": int(previous_complaints)
            }])
            
            pred = model.predict(input_df)[0]
            risk_level = str(pred)

            if hasattr(model, "predict_proba"):
                probas = model.predict_proba(input_df)[0]
                classes = model.classes_
                prob_map = {str(c): float(p) for c, p in zip(classes, probas)}
                confidence = round(max(prob_map.values()), 2)
                
                # If high probability for HIGH risk
                if "HIGH" in prob_map and prob_map["HIGH"] > 0.45:
                    risk_score = max(risk_score, round(0.75 + prob_map["HIGH"] * 0.20, 2))
        except Exception as e:
            print(f"ML Model prediction exception: {e}")

    if risk_score >= 0.70:
        risk_level = "HIGH"
    elif risk_score >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    # Match high-risk cash-out location demo
    cash_out = {
        "locationName": "SBI ATM, Master Canteen Square, Bhubaneswar",
        "latitude": 20.2961,
        "longitude": 85.8245,
        "suspiciousTxCount": 14,
        "relatedCasesCount": 6,
        "lastTxTime": "12 mins ago",
        "predictedRisk": risk_level
    }

    return {
        "riskScore": risk_score,
        "riskLevel": risk_level,
        "confidence": confidence,
        "cashOutLocation": cash_out
    }
