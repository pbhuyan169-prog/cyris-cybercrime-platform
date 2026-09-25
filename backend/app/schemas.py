from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth & OTP Schemas ---
class RequestOTP(BaseModel):
    identifier: str # phone or email

class VerifyOTP(BaseModel):
    identifier: str
    otp_code: str
    full_name: Optional[str] = "Citizen User"

class AuthorityLogin(BaseModel):
    authority_type: str # POLICE, CYBER_AUTHORITY, BANK_AUTHORITY
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    authority_type: Optional[str] = None
    username: str
    masked_identifier: Optional[str] = None

# --- Complaint Schemas ---
class ComplaintCreate(BaseModel):
    full_name: str
    phone_number: str
    email: Optional[str] = None
    fraud_type: str # UPI_FRAUD, BANKING_FRAUD, ATM_FRAUD, PHISHING, SOCIAL_MEDIA_SCAM, ONLINE_SHOPPING
    transaction_id: Optional[str] = None
    amount: float
    upi_id: Optional[str] = None
    city: Optional[str] = "Bhubaneswar"
    state: Optional[str] = "Odisha"
    latitude: Optional[float] = 20.2961
    longitude: Optional[float] = 85.8245
    description: str

class ComplaintResponse(BaseModel):
    complaintId: str
    fullName: str
    phoneNumberMasked: str
    emailMasked: Optional[str] = None
    fraudType: str
    transactionId: Optional[str] = None
    amount: float
    upiIdMasked: Optional[str] = None
    city: str
    state: str
    location: Dict[str, float]
    description: str
    status: str
    assignedAuthority: str
    timestamp: str
    riskScore: Optional[float] = None
    riskLevel: Optional[str] = None

class ComplaintStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None

# --- Bank Transaction Schemas ---
class TransactionResponse(BaseModel):
    transactionId: str
    senderAccountMasked: str
    receiverUpiMasked: str
    amount: float
    timestamp: str
    txType: str
    atmLocation: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    status: str

# --- ML Prediction Schemas ---
class PredictionRequest(BaseModel):
    fraudType: str
    amount: float
    hourOfDay: Optional[int] = 14
    victimAgeGroup: Optional[str] = "26-40"
    deviceRisk: Optional[float] = 5.0
    locationRisk: Optional[float] = 6.0
    previousComplaints: Optional[int] = 0

class PredictionResponse(BaseModel):
    complaintId: str
    riskScore: float
    riskLevel: str # LOW, MEDIUM, HIGH
    confidence: float
    predictionStatus: str # Pending Verification, Verified, Rejected
    cashOutLocation: Optional[Dict[str, Any]] = None

class PredictionVerification(BaseModel):
    status: str # Verified, Rejected, Under Review
    notes: Optional[str] = None

# --- GIS Location Schemas ---
class RiskLocationResponse(BaseModel):
    id: int
    name: str
    city: str
    state: str
    latitude: float
    longitude: float
    riskLevel: str
    relatedCasesCount: int
    suspiciousTxCount: int
    riskScore: float
    lastTxTime: str

# --- Alert Schemas ---
class AlertResponse(BaseModel):
    id: int
    complaintId: str
    riskScore: float
    locationName: str
    reason: str
    verificationStatus: str
    timestamp: str
    fraudType: Optional[str] = None
    amount: Optional[float] = None

class AlertStatusUpdate(BaseModel):
    status: str # Verified, Rejected, Under Review
