import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from supabase import create_client, Client

from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.routers import auth, complaints, bank, predictions, gis, alerts, analytics
from backend.app.websocket_manager import manager
from backend.app.services.ml_service import load_ml_model

# --- SUPABASE CONFIGURATION ---
SUPABASE_URL = os.getenv("SUPABASE_URL", settings.SUPABASE_URL if hasattr(settings, "SUPABASE_URL") else "https://YOUR_SUPABASE_PROJECT_ID.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", settings.SUPABASE_KEY if hasattr(settings, "SUPABASE_KEY") else "YOUR_SUPABASE_ANON_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- REQUEST MODELS FOR OTP ---
class SendOtpRequest(BaseModel):
    email: str

class VerifyOtpRequest(BaseModel):
    email: str
    token: str
    role: str = "Citizen User"

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Smart India Hackathon 2026 Prototype Backend"
)

# Enable CORS for cross-origin teammates access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(bank.router)
app.include_router(predictions.router)
app.include_router(gis.router)
app.include_router(alerts.router)
app.include_router(analytics.router)

# --- REAL-TIME SUPABASE OTP AUTHENTICATION ENDPOINTS ---

@app.post("/api/v1/auth/send-otp")
def send_otp(req: SendOtpRequest):
    """Triggers a real-time OTP code sent to the specified email via Supabase."""
    try:
        res = supabase.auth.sign_in_with_otp({"email": req.email})
        return {"status": "success", "message": f"OTP sent successfully to {req.email}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/v1/auth/verify-otp")
def verify_otp(req: VerifyOtpRequest):
    """Verifies the incoming real-time OTP code against Supabase Auth."""
    try:
        res = supabase.auth.verify_otp({
            "email": req.email,
            "token": req.token,
            "type": "email"
        })
        
        if res.user:
            return {
                "status": "success",
                "message": "Authenticated succes