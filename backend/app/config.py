import os

class Settings:
    PROJECT_NAME: str = "CYRIS - Predictive Analytics Framework for Cybercrime Complaints"
    VERSION: str = "3.0.0"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "cyris-hackathon-2026-secure-jwt-key-super-secret-key-321")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "https://pyolsspjnxmqzxdlgkuh.supabase.co")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "sb_publishable_YcZeqCwDFpmZdJ83-99diw_Gs64RRJ-")
    
    # Database
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATABASE_URL: str = os.getenv("SUPABASE_DATABASE_URL", os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'cyris.db')}"))
    
    # ML & Risk Thresholds
    RISK_ALERT_THRESHOLD: float = 0.70 # Trigger investigator alert if risk score >= 0.70
    MODEL_PATH: str = os.path.join(BASE_DIR, "ml", "cyris_risk_model.pkl")

settings = Settings()
