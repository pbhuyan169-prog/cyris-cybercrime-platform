from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.app.database import get_db
from backend.app.models import User, OTPRecord
from backend.app.schemas import RequestOTP, VerifyOTP, AuthorityLogin, TokenResponse
from backend.app.security import (
    generate_otp, hash_password, verify_password, create_access_token,
    mask_phone, mask_email
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

@router.post("/register-otp")
def request_otp(data: RequestOTP, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    if not identifier:
        raise HTTPException(status_code=400, detail="Mobile number or Email is required")
    
    otp_code = generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    # Store OTP in DB
    otp_entry = OTPRecord(
        identifier=identifier,
        otp_code=otp_code,
        expires_at=expires_at,
        verified=False
    )
    db.add(otp_entry)
    db.commit()
    
    masked = mask_phone(identifier) if identifier.isdigit() or "+" in identifier else mask_email(identifier)
    
    return {
        "success": True,
        "message": f"Real-Time OTP sent to {masked}",
        "otp_simulated": otp_code, # For hackathon presentation preview
        "expires_in_seconds": 300
    }

@router.post("/verify-otp", response_model=TokenResponse)
def verify_otp(data: VerifyOTP, db: Session = Depends(get_db)):
    identifier = data.identifier.strip()
    otp_code = data.otp_code.strip()
    
    record = db.query(OTPRecord).filter(
        OTPRecord.identifier == identifier,
        OTPRecord.otp_code == otp_code,
        OTPRecord.verified == False
    ).order_by(OTPRecord.id.desc()).first()
    
    if not record:
        # Fallback bypass for hackathon demo if OTP is "123456"
        if otp_code != "123456":
            raise HTTPException(status_code=400, detail="Invalid or expired OTP")
    else:
        record.verified = True
        db.commit()
        
    # Check if User exists
    user = db.query(User).filter(
        (User.phone == identifier) | (User.email == identifier)
    ).first()
    
    if not user:
        # Create citizen user
        user = User(
            username=f"citizen_{identifier[-4:] if len(identifier)>=4 else 'user'}",
            email=identifier if "@" in identifier else f"{identifier}@citizen.portal",
            phone=identifier if "@" not in identifier else "+919876543210",
            hashed_password=hash_password("citizen_pass"),
            role="CITIZEN",
            authority_type=None
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
    access_token = create_access_token(data={
        "sub": user.username,
        "role": "CITIZEN",
        "user_id": user.id
    })
    
    masked = mask_phone(user.phone) if "@" not in user.phone else mask_email(user.email)
    
    return TokenResponse(
        access_token=access_token,
        role="CITIZEN",
        authority_type=None,
        username=user.username,
        masked_identifier=masked
    )

@router.post("/authority-login", response_model=TokenResponse)
def authority_login(data: AuthorityLogin, db: Session = Depends(get_db)):
    auth_type = data.authority_type.upper().strip()
    valid_roles = ["POLICE", "CYBER_AUTHORITY", "BANK_AUTHORITY"]
    if auth_type not in valid_roles:
        raise HTTPException(status_code=400, detail="Invalid authority type selected")
        
    user = db.query(User).filter(
        User.username == data.username,
        User.authority_type == auth_type
    ).first()
    
    # Auto-provision hackathon authority user if missing for seamless testing
    if not user:
        user = User(
            username=data.username,
            email=f"{data.username.lower()}@cyris.gov.in",
            phone="+919999999999",
            hashed_password=hash_password(data.password),
            role=auth_type,
            authority_type=auth_type
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not verify_password(data.password, user.hashed_password):
            # Fallback check for demo credentials
            if data.password != "admin123":
                raise HTTPException(status_code=401, detail="Invalid authority credentials")
                
    access_token = create_access_token(data={
        "sub": user.username,
        "role": auth_type,
        "authority_type": auth_type,
        "user_id": user.id
    })
    
    return TokenResponse(
        access_token=access_token,
        role=auth_type,
        authority_type=auth_type,
        username=user.username,
        masked_identifier=mask_email(user.email)
    )
