import os
import sys

# Ensure backend root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.config import settings
from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, Complaint
from backend.seed_data import seed_database
from backend.app.websocket_manager import manager

# Routers
from backend.app.routers import auth, complaints, predictions, gis, bank, alerts, analytics

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="CYRIS Predictive Analytics Framework with Supabase Backend & Real-Time Alert Engine"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include All Routers
app.include_router(auth.router)
app.include_router(complaints.router)
app.include_router(predictions.router)
app.include_router(gis.router)
app.include_router(bank.router)
app.include_router(alerts.router)
app.include_router(analytics.router)

# Compatibility aliases for /api/v1 prefix (Streamlit & mobile clients)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(complaints.router, prefix="/api/v1")

# Additional Streamlit specific auth & complaints routes
@app.post("/api/v1/auth/send-otp")
def stream_send_otp(req: auth.SendOtpRequest, db=Depends(auth.get_db)):
    return auth.request_otp(auth.RequestOTP(identifier=req.email), db=db)

@app.post("/api/v1/auth/verify-otp")
def stream_verify_otp(req: auth.StreamlitVerifyOtpRequest, db=Depends(auth.get_db)):
    return auth.verify_otp(auth.VerifyOTP(identifier=req.email, otp_code=req.token, full_name=req.role), db=db)

@app.get("/api/v1/complaints")
def stream_get_complaints(search: str = None, status: str = None, db=Depends(auth.get_db)):
    complaints_list = complaints.list_complaints(search=search, status=status, db=db)
    return {"complaints": complaints_list}

@app.post("/api/v1/complaints")
async def stream_submit_complaint(payload: dict, db=Depends(auth.get_db)):
    return await complaints.submit_complaint(payload=payload, db=db)


# Static Files Setup
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
INDEX_HTML_PATH = os.path.join(BASE_DIR, "index.html")

if os.path.exists(FRONTEND_DIR):
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.on_event("startup")
def on_startup():
    """Ensure DB schema exists and seed data if DB is empty."""
    print(f"Connecting to database via SQLAlchemy ({settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else 'local'})...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        complaint_count = db.query(Complaint).count()
        if user_count == 0 or complaint_count == 0:
            print("Database empty. Initializing default demonstration data...")
            seed_database()
    except Exception as e:
        print("Startup DB check notice:", e)
    finally:
        db.close()


@app.get("/portal", response_class=FileResponse)
def serve_portal():
    """Serves the main CYRIS Web Application Dashboard UI."""
    if not os.path.exists(INDEX_HTML_PATH):
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(INDEX_HTML_PATH)


@app.get("/")
def read_root():
    """Root metadata & endpoint sitemap."""
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "supabase_connected": True,
        "portal_url": "/portal",
        "api_docs": "/docs",
        "websocket_url": "/ws/alerts"
    }


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """Real-Time Alert WebSocket Feed for Authority Dashboard."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive loop
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)