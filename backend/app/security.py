import random
import string
import hashlib
from datetime import datetime, timedelta
import jwt
from backend.app.config import settings

# --- Entity Masking Utilities ---
def mask_phone(phone: str) -> str:
    if not phone or len(phone) < 7:
        return "XXXXXX"
    clean = phone.strip()
    return f"{clean[:3]}****{clean[-4:]}"

def mask_upi(upi: str) -> str:
    if not upi or "@" not in upi:
        return "xxxx@upi"
    handle, domain = upi.split("@", 1)
    if len(handle) <= 2:
        masked_handle = handle[0] + "*"
    else:
        masked_handle = handle[0] + "*" * (len(handle) - 2) + handle[-1]
    return f"{masked_handle}@{domain}"

def mask_account(account: str) -> str:
    if not account or len(account) < 4:
        return "XXXX-XXXX-0000"
    clean = account.replace("-", "").replace(" ", "")
    return f"XXXX-XXXX-{clean[-4:]}"

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "x***x@domain.com"
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        masked_name = name[0] + "*"
    else:
        masked_name = name[0] + "*" * (len(name) - 2) + name[-1]
    return f"{masked_name}@{domain}"


# --- Password Hashing ---
def hash_password(password: str) -> str:
    return hashlib.sha256((password + settings.SECRET_KEY).encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password


# --- JWT Tokens ---
def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None


# --- OTP Utilities ---
def generate_otp() -> str:
    # 6-digit numeric OTP
    return "".join(random.choices(string.digits, k=6))
