from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False) # CITIZEN, POLICE, CYBER_AUTHORITY, BANK_AUTHORITY, ADMIN
    authority_type = Column(String, nullable=True) # POLICE, CYBER_AUTHORITY, BANK_AUTHORITY
    created_at = Column(DateTime, default=datetime.utcnow)

class OTPRecord(Base):
    __tablename__ = "otp_records"

    id = Column(Integer, primary_key=True, index=True)
    identifier = Column(String, index=True, nullable=False) # phone or email
    otp_code = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, unique=True, index=True, nullable=False) # CMP-2026-XXXX
    citizen_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    fraud_type = Column(String, nullable=False) # UPI_FRAUD, BANKING_FRAUD, ATM_FRAUD, PHISHING, SOCIAL_MEDIA_SCAM, ONLINE_SHOPPING
    transaction_id = Column(String, index=True, nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    upi_id = Column(String, index=True, nullable=True)
    city = Column(String, nullable=False, default="Bhubaneswar")
    state = Column(String, nullable=False, default="Odisha")
    latitude = Column(Float, nullable=False, default=20.2961)
    longitude = Column(Float, nullable=False, default=85.8245)
    description = Column(Text, nullable=False)
    evidence_filename = Column(String, nullable=True)
    status = Column(String, default="Under Review") # Under Review, Pending Bank Freeze, Escalated, Action Taken, Resolved
    assigned_authority = Column(String, default="CYBER_AUTHORITY") # Default recipient
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    predictions = relationship("Prediction", back_populates="complaint", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="complaint", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, ForeignKey("complaints.complaint_id"), nullable=False)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(String, unique=True, index=True, nullable=False) # TXN-XXXX
    sender_account_masked = Column(String, nullable=False) # XXXX-XXXX-4921
    receiver_upi = Column(String, nullable=True) # scammer@upi
    amount = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    tx_type = Column(String, nullable=False) # UPI, ATM, NET_BANKING, DEBIT_CARD
    atm_location = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    status = Column(String, default="FLAGGED") # COMPLETED, FLAGGED, BLOCKED, UNDER_INVESTIGATION

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False, default="Odisha")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    risk_level = Column(String, default="MEDIUM") # LOW, MEDIUM, HIGH, CRITICAL
    related_cases_count = Column(Integer, default=1)
    suspicious_tx_count = Column(Integer, default=1)
    last_tx_time = Column(String, nullable=True)

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, ForeignKey("complaints.complaint_id"), nullable=False)
    risk_score = Column(Float, nullable=False) # 0.00 - 1.00
    risk_level = Column(String, nullable=False) # LOW, MEDIUM, HIGH
    confidence = Column(Float, default=0.85)
    features_json = Column(Text, nullable=True)
    status = Column(String, default="Pending Verification") # Pending Verification, Verified, Rejected
    verified_by = Column(String, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="predictions")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, ForeignKey("complaints.complaint_id"), nullable=False)
    risk_score = Column(Float, nullable=False)
    location_name = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    verification_status = Column(String, default="Pending") # Pending, Verified, Rejected, Under Review
    timestamp = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="alerts")

class RelatedCase(Base):
    __tablename__ = "related_cases"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id_1 = Column(String, nullable=False)
    complaint_id_2 = Column(String, nullable=False)
    similarity_reason = Column(String, nullable=False) # Same UPI ID, Same Phone, Same Location
    similarity_score = Column(Float, default=0.90)

class InvestigationUpdate(Base):
    __tablename__ = "investigation_updates"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(String, nullable=False)
    authority_user = Column(String, nullable=False)
    authority_role = Column(String, nullable=False)
    status_from = Column(String, nullable=False)
    status_to = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(Text, nullable=True)
