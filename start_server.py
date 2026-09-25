import uvicorn
import os
import sys

if __name__ == "__main__":
    print("Starting CYRIS Backend & Frontend Server...")
    print("Local URL: http://localhost:8000/portal")
    print("API Specs: http://localhost:8000/docs")
    print("WebSocket: ws://localhost:8000/ws/alerts")
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
