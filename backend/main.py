import json
import os
import uuid
import os
import joblib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COMPLAINT_MODEL_PATH = os.path.join(
    BASE_DIR,
    "ml",
    "cyris_risk_model.pkl"
)
if not os.path.exists(COMPLAINT_MODEL_PATH):
    COMPLAINT_MODEL_PATH = os.path.join(BASE_DIR, "cyris_risk_model_optimized.pkl")

try:
    complaint_risk_model = joblib.load(COMPLAINT_MODEL_PATH)
    print("OK: Complaint risk model loaded")
    COMPLAINT_RISK_ENABLED = True
except Exception as e:
    print("WARNING: Complaint risk model not loaded:", e)
    complaint_risk_model = None
    COMPLAINT_RISK_ENABLED = False
import pandas as pd

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.graph_engine import CyrisGraphEngine
from backend.nlp_pipeline import CyrisNLPClassifier


# ============================================================
# CYRIS APPLICATION
# ============================================================

app = FastAPI(
    title="Cyris Cybercrime Analytics Platform",
    version="2.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PATHS
# ============================================================

BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(BACKEND_DIR)

DATA_PATH = os.path.join(
    BASE_DIR,
    "mock_data.json"
)

OLD_MODEL_PATH = os.path.join(
    BACKEND_DIR,
    "cyris_risk_model.pkl"
)

ATM_MODEL_PATH = os.path.join(
    BACKEND_DIR,
    "cyris_atm_risk_model.pkl"
)

HOTSPOT_MODEL_PATH = os.path.join(
    BACKEND_DIR,
    "cyris_atm_hotspot_model.pkl"
)

HOTSPOT_DATA_PATH = os.path.join(
    BACKEND_DIR,
    "cyris_atm_hotspots.json"
)


# ============================================================
# LOAD EXISTING ENGINES
# ============================================================

graph_engine = CyrisGraphEngine(DATA_PATH)
nlp_engine = CyrisNLPClassifier()


# ============================================================
# LOAD MACHINE LEARNING MODELS
# ============================================================

risk_model = None
atm_risk_model = None
hotspot_model = None


# ----- Existing complaint risk model -----

if os.path.exists(OLD_MODEL_PATH):
    try:
        risk_model = joblib.load(OLD_MODEL_PATH)
        print("OK: Complaint risk model loaded")
    except Exception as e:
        print("WARNING: Could not load complaint risk model:", e)
else:
    print("WARNING: cyris_risk_model.pkl not found")


# ----- New ATM risk model -----

if os.path.exists(ATM_MODEL_PATH):
    try:
        atm_risk_model = joblib.load(ATM_MODEL_PATH)
        print("OK: ATM risk model loaded")
    except Exception as e:
        print("WARNING: Could not load ATM risk model:", e)
else:
    print("WARNING: cyris_atm_risk_model.pkl not found")


# ----- New hotspot model -----

if os.path.exists(HOTSPOT_MODEL_PATH):
    try:
        hotspot_model = joblib.load(HOTSPOT_MODEL_PATH)
        print("OK: ATM hotspot model loaded")
    except Exception as e:
        print("WARNING: Could not load ATM hotspot model:", e)
else:
    print("WARNING: cyris_atm_hotspot_model.pkl not found")


# ============================================================
# INPUT MODEL
# ============================================================

class ComplaintInput(BaseModel):
    description: str


# ============================================================
# LOAD RAW DATA
# ============================================================

def load_raw_data():

    if not os.path.exists(DATA_PATH):
        raise HTTPException(
            status_code=500,
            detail="mock_data.json not found"
        )

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def read_root():

    return {
        "status": "Cyris Engine Active",
        "version": "2.0.0",
        "modules": {
            "complaint_risk": risk_model is not None,
            "atm_risk": atm_risk_model is not None,
            "atm_hotspot": hotspot_model is not None,
            "graph_analysis": True,
            "nlp_classification": True
        }
    }


# ============================================================
# 1. COMPLAINT DETAILS + GRAPH
# ============================================================

@app.get("/api/complaint/{complaint_id}")
def get_complaint(complaint_id: str):

    data = load_raw_data()

    complaint = next(
        (
            c for c in data
            if c.get("complaint_id") == complaint_id
        ),
        None
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    connected = graph_engine.find_connected_cases(
        complaint_id
    )

    return {
        "case_details": complaint,
        "connected_case_ids": connected,
        "is_syndicate": len(connected) > 0
    }


# ============================================================
# 2. FRAUD RINGS
# ============================================================

@app.get("/api/patterns/fraud-rings")
def get_fraud_rings():

    return {
        "fraud_rings": graph_engine.get_fraud_rings()
    }


# ============================================================
# 3. CYRIS HOTSPOT MAP
# ============================================================

@app.get("/api/analytics/hotspots")
def get_hotspots():

    # Use trained hotspot results if available

    if os.path.exists(HOTSPOT_DATA_PATH):

        try:

            with open(
                HOTSPOT_DATA_PATH,
                "r",
                encoding="utf-8"
            ) as f:

                hotspots = json.load(f)

            return {
                "total": len(hotspots),
                "hotspots": hotspots,
                "source": "CYRIS trained ATM hotspot model"
            }

        except Exception as e:

            print(
                "Could not read hotspot file:",
                e
            )


    # Fallback to existing complaint locations

    data = load_raw_data()

    hotspots = []

    for item in data:

        if item.get("latitude") is None:
            continue

        hotspots.append(
            {
                "complaint_id":
                    item.get("complaint_id"),

                "crime_type":
                    item.get("crime_type"),

                "city":
                    item.get("location", ""),

                "latitude":
                    item.get("latitude", 20.5937),

                "longitude":
                    item.get("longitude", 78.9629),

                "risk_level":
                    item.get("risk_level", "UNKNOWN")
            }
        )

    return {
        "total": len(hotspots),
        "hotspots": hotspots,
        "source": "complaint data fallback"
    }


# ============================================================
# 4. ATM RISK PREDICTION
# ============================================================

@app.post("/api/analytics/atm-risk")
def predict_atm_risk(data: dict):

    if atm_risk_model is None:

        raise HTTPException(
            status_code=500,
            detail="ATM risk model is not loaded"
        )

    try:

        # ----------------------------------------------------
        # Convert frontend field names into model field names
        # ----------------------------------------------------

        input_data = {

            "crime_type":
                data.get(
                    "crime_type",
                    "ATM Fraud"
                ),

            "sub_type":
                data.get(
                    "sub_type",
                    "Cash Withdrawal Fraud"
                ),

            "amount_lost":
                float(
                    data.get(
                        "amount_lost",
                        data.get(
                            "transaction_amount",
                            0
                        )
                    )
                ),

            "state":
                data.get(
                    "state",
                    ""
                ),

            "city":
                data.get(
                    "city",
                    data.get(
                        "location",
                        ""
                    )
                ),

            "latitude":
                float(
                    data.get(
                        "latitude",
                        20.5937
                    )
                ),

            "longitude":
                float(
                    data.get(
                        "longitude",
                        78.9629
                    )
                ),

            "transaction_type":
                data.get(
                    "transaction_type",
                    "ATM Withdrawal"
                ),

            "transaction_count":
                int(
                    data.get(
                        "transaction_count",
                        1
                    )
                ),

            "suspicious_transactions":
                int(
                    data.get(
                        "suspicious_transactions",
                        1
                    )
                ),

            "previous_complaints":
                int(
                    data.get(
                        "previous_complaints",
                        0
                    )
                ),

            "complaint_hour":
                int(
                    data.get(
                        "complaint_hour",
                        12
                    )
                ),

            "day_of_week":
                data.get(
                    "day_of_week",
                    "Monday"
                ),

            "location_risk":
                data.get(
                    "location_risk",
                    "Medium"
                ),

            "victim_age_group":
                data.get(
                    "victim_age_group",
                    "26-40"
                ),

            "device_risk":
                data.get(
                    "device_risk",
                    "Medium"
                ),

            "account_age_days":
                int(
                    data.get(
                        "account_age_days",
                        100
                    )
                ),

            "distance_from_complainant_km":
                float(
                    data.get(
                        "distance_from_complainant_km",
                        2
                    )
                ),

            "channel":
                data.get(
                    "channel",
                    "ATM"
                ),

            "suspicious_transaction":
                int(
                    data.get(
                        "suspicious_transaction",
                        1
                    )
                ),

            "risk_score":
                float(
                    data.get(
                        "risk_score",
                        50
                    )
                )
        }


        # ----------------------------------------------------
        # DataFrame
        # ----------------------------------------------------

        X = pd.DataFrame(
            [input_data]
        )


        # ----------------------------------------------------
        # Prediction
        # ----------------------------------------------------

        prediction = atm_risk_model.predict(X)[0]


        # ----------------------------------------------------
        # Probability
        # ----------------------------------------------------

        probabilities = {}

        if hasattr(
            atm_risk_model,
            "predict_proba"
        ):

            proba = atm_risk_model.predict_proba(X)[0]

            classes = (
                atm_risk_model
                .named_steps["classifier"]
                .classes_
            )

            probabilities = {
                str(cls): round(
                    float(prob) * 100,
                    2
                )
                for cls, prob in zip(
                    classes,
                    proba
                )
            }

            confidence = max(
                probabilities.values()
            )

        else:

            confidence = 0


        return {

            "success": True,

            "prediction": {
                "risk_level":
                    str(prediction),

                "confidence":
                    round(
                        confidence,
                        2
                    ),

                "probabilities":
                    probabilities
            },

            "input":
                input_data
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"ATM prediction failed: {str(e)}"
        )


# ============================================================
# 5. TOP ATM RISK ZONES
# ============================================================

@app.get("/api/analytics/atm-risk-zones")
def get_atm_risk_zones():

    if not os.path.exists(
        HOTSPOT_DATA_PATH
    ):

        raise HTTPException(
            status_code=404,
            detail="ATM hotspot data not found"
        )

    try:

        with open(
            HOTSPOT_DATA_PATH,
            "r",
            encoding="utf-8"
        ) as f:

            hotspots = json.load(f)


        # Highest-risk zones first

        hotspots = sorted(
            hotspots,
            key=lambda x:
                x.get(
                    "hotspot_score",
                    0
                ),
            reverse=True
        )


        return {

            "success": True,

            "total_zones":
                len(hotspots),

            "critical_zones":
                [
                    x for x in hotspots
                    if x.get(
                        "hotspot_level"
                    ) == "CRITICAL"
                ],

            "high_risk_zones":
                [
                    x for x in hotspots
                    if x.get(
                        "hotspot_level"
                    ) == "HIGH"
                ],

            "top_zones":
                hotspots[:10]
        }


    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not load ATM zones: {str(e)}"
        )


# ============================================================
# 6. GLOBAL SEARCH
# ============================================================

@app.get("/api/search")
def search_complaints(query: str):

    data = load_raw_data()

    query_lower = query.lower()

    results = [

        c for c in data

        if (
            query_lower
            in str(
                c.get(
                    "complaint_id",
                    ""
                )
            ).lower()
        )

        or (
            query_lower
            in str(
                c.get(
                    "upi_id",
                    ""
                )
            ).lower()
        )

        or (
            query_lower
            in str(
                c.get(
                    "phone_number",
                    ""
                )
            ).lower()
        )

        or (
            query_lower
            in str(
                c.get(
                    "crime_type",
                    ""
                )
            ).lower()
        )
    ]

    return {
        "count": len(results),
        "results": results
    }


# ============================================================
# 7. SUBMIT CYBERCRIME COMPLAINT
# ============================================================

@app.post("/api/complaints")
def submit_complaint(complaint: dict):

    complaint_id = (
        "CMP-"
        + uuid.uuid4()
        .hex[:8]
        .upper()
    )

    new_complaint = {

        "complaint_id":
            complaint_id,

        "name":
            complaint.get(
                "name",
                ""
            ),

        "phone_number":
            complaint.get(
                "phone",
                ""
            ),

        "email":
            complaint.get(
                "email",
                ""
            ),

        "crime_type":
            complaint.get(
                "crime_type",
                ""
            ),

        "transaction_id":
            complaint.get(
                "transaction_id",
                ""
            ),

        "transaction_amount":
            complaint.get(
                "transaction_amount",
                0
            ),

        "upi_id":
            complaint.get(
                "upi_id",
                ""
            ),

        "location":
            complaint.get(
                "location",
                ""
            ),

        "description":
            complaint.get(
                "description",
                ""
            ),

        "status":
            "Under Review"
    }

    data = load_raw_data()

    data.append(
        new_complaint
    )

    with open(
        DATA_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4
        )

    return {

        "success": True,

        "complaint_id":
            complaint_id,

        "status":
            "Under Review",

        "message":
            "Complaint submitted successfully"
    }


# ============================================================
# 8. NLP CLASSIFICATION
# ============================================================

@app.post("/api/ai/classify")
def classify_text(
    input_data: ComplaintInput
):

    if not input_data.description.strip():

        raise HTTPException(
            status_code=400,
            detail="Description text cannot be empty"
        )

    classification = (
        nlp_engine.classify_complaint(
            input_data.description
        )
    )

    return {

        "input_text":
            input_data.description,

        "classification":
            classification
    }


# ============================================================
# 9. DASHBOARD STATISTICS
# ============================================================

@app.get("/api/dashboard/stats")
def dashboard_stats():

    data = load_raw_data()

    total = len(data)

    under_review = sum(
        1
        for item in data
        if item.get(
            "status",
            "Under Review"
        ) == "Under Review"
    )

    investigation = sum(
        1
        for item in data
        if item.get(
            "status"
        ) == "Investigation Started"
    )

    action_taken = sum(
        1
        for item in data
        if item.get(
            "status"
        ) == "Action Taken"
    )

    resolved = sum(
        1
        for item in data
        if item.get(
            "status"
        ) == "Resolved"
    )

    return {

        "total":
            total,

        "under_review":
            under_review,

        "investigation":
            investigation,

        "action_taken":
            action_taken,

        "resolved":
            resolved
    }
class ComplaintRiskRequest(BaseModel):
    crime_type: str
    sub_type: str
    amount_lost: float
    state: str
    city: str
    latitude: float
    longitude: float
    transaction_type: str
    transaction_count: int
    suspicious_transactions: int
    previous_complaints: int
    complaint_hour: int
    day_of_week: int
    location_risk: float
    victim_age_group: str
    device_risk: float
    account_age_days: int
    distance_from_complainant_km: float
    channel: str
    suspicious_transaction: int  
@app.post("/api/complaints/risk")
def predict_complaint_risk(data: ComplaintRiskRequest):

    if complaint_risk_model is None:
        raise HTTPException(
            status_code=503,
            detail="Complaint risk model is not loaded"
        )

    try:
        input_data = pd.DataFrame([{
            "crime_type": data.crime_type,
            "sub_type": data.sub_type,
            "amount_lost": data.amount_lost,
            "state": data.state,
            "city": data.city,
            "latitude": data.latitude,
            "longitude": data.longitude,
            "transaction_type": data.transaction_type,
            "transaction_count": data.transaction_count,
            "suspicious_transactions": data.suspicious_transactions,
            "previous_complaints": data.previous_complaints,
            "complaint_hour": data.complaint_hour,
            "day_of_week": data.day_of_week,
            "location_risk": data.location_risk,
            "victim_age_group": data.victim_age_group,
            "device_risk": data.device_risk,
            "account_age_days": data.account_age_days,
            "distance_from_complainant_km": data.distance_from_complainant_km,
            "channel": data.channel,
            "suspicious_transaction": data.suspicious_transaction
        }])

        prediction = complaint_risk_model.predict(input_data)[0]

        result = {
            "risk_level": str(prediction)
        }

        # Get confidence if the model supports probabilities
        if hasattr(complaint_risk_model, "predict_proba"):
            probabilities = complaint_risk_model.predict_proba(input_data)[0]
            classes = complaint_risk_model.classes_

            probability_map = {
                str(cls): float(prob)
                for cls, prob in zip(classes, probabilities)
            }

            result["confidence"] = round(
                max(probability_map.values()),
                4
            )

            result["probabilities"] = probability_map

        return result

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Complaint risk prediction failed: {str(e)}"
        )