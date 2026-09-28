import uvicorn
import os
import sys

# Ensure project root is in sys.path and is current working directory
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

if __name__ == "__main__":
    print("Starting CYRIS Backend & Frontend Server...")
    print("Local URL: http://localhost:8000/portal")
    print("API Specs: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/alerts")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
