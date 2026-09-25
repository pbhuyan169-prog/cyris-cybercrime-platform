# CYRIS - Predictive Analytics Framework for Cybercrime Complaints

> **Smart India Hackathon (SIH 2026) Working Full-Stack Prototype**
> **Theme**: Blockchain & Cybersecurity
> **Objective**: Integrated real-time platform connecting Citizen Complaint Portal, Multi-Agency Authority Dashboards (Police, Cyber Authority, Bank Nodal Officers), AI/ML Predictive Risk Engine, Mock Bank REST API, and Leaflet GIS Cash-Out Hotspot Analytics.

---

## 🌟 System Features & Architecture

### 1. Backend Architecture (`/backend`)
- **FastAPI Core**: Modular Python backend handling REST APIs, JWT authentication, and WebSockets.
- **Single Folder Backend**: All database ORM models, routes, services, security, and ML logic reside inside `backend/`.
- **Database (`SQLAlchemy`)**: SQLite out-of-the-box (`cyris.db`), fully compatible with PostgreSQL via `DATABASE_URL`.
- **Real-Time WebSockets (`/ws/alerts`)**: Pushes instant live alerts and new complaint events to all connected teammate browsers in real-time.

### 2. Citizen Portal
- **Real-Time OTP Authentication**: Simulates SMS & Email OTP generation and verification for secure Citizen registration and login.
- **Cybercrime Reporting**: Supports fraud types (`UPI Fraud`, `Online Banking Fraud`, `ATM Fraud`, `Phishing`, `Social Media Scam`, `Online Shopping Fraud`).
- **Unique Complaint ID Generation**: Creates unique identifiers (`CMP-2026-XXXX`).
- **Default Routing**: All newly registered citizen complaints are automatically routed to the **Cyber Authority** dashboard.
- **Access Isolation**: Citizens can view only their own complaints and updates. Investigation data and other citizens' reports remain protected.

### 3. Multi-Persona Authority Portal (3 Login Options)
Option selector on Authority Login Page:
1. **Police / Investigator** (`police_officer` / `admin123`)
2. **Cyber Authority** (`cyber_authority` / `admin123`)
3. **Bank Authority** (`bank_officer` / `admin123`)

Features:
- **Search & Complaint Filter**: Search by Complaint ID, UPI ID, Phone Number, or Fraud Type.
- **Authorised Entity Linkage (Masked)**: Protects privacy by masking phone numbers (`+91 98****3210`), UPI IDs (`f***h@ybl`), and bank account numbers (`XXXX-XXXX-4921`).
- **Network Synergy**: Displays related/similar complaints matching suspect receiver UPI IDs or phone numbers.
- **AI/ML Decision Support**: Displays AI Risk Score (0.00-1.00), Risk Level (`LOW`, `MEDIUM`, `HIGH`), Model Confidence, and **Human-in-the-Loop Verification** controls (`Verify Prediction` / `Reject Prediction`).
- **Leaflet GIS Map**: Interactive map displaying color-coded high-risk cash-out locations with popups showing related cases, suspicious transactions count, and last transaction time.
- **Bank Transaction Inspection**: Dedicated REST endpoint (`GET /api/transactions/{id}`) to query transaction details from the Bank module.

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.9+ installed.

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Seed Database with Dummy Data & Demo Case
```bash
python backend/seed_data.py
```

### 3. Start Full-Stack Application Server
```bash
python start_server.py
```
Or directly via uvicorn:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Open in Browser
- **Web App Dashboard**: [http://localhost:8000/portal](http://localhost:8000/portal)
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Real-Time WebSocket Alert Feed**: `ws://localhost:8000/ws/alerts`

---

## 🎬 Demonstration Scenario (Step-by-Step)

1. Open [http://localhost:8000/portal](http://localhost:8000/portal) in your browser.
2. **Citizen Portal**:
   - Click **Enter Citizen Portal**.
   - Fill out a cybercrime report:
     - **Name**: `Rajesh Mohanty`
     - **Mobile**: `+91 98765 43210`
     - **Fraud Type**: `UPI Fraud`
     - **Amount**: `₹25,000`
     - **Receiver UPI**: `fastcash.refund@ybl`
     - **Description**: `Victim clicked a fraudulent WhatsApp refund link resulting in unauthorized UPI debit.`
   - Click **Register Cybercrime Complaint**.
   - Input the simulated 6-digit OTP (or click **Verify OTP & Continue**).
   - System displays generated Complaint ID `CMP-2026-XXXX`.
3. **Authority Portal**:
   - Return to Home, click **Select Authority Portal**.
   - Select **Option 1: Cyber Authority**, enter Username `cyber_authority` & Password `admin123`.
   - The dashboard opens showcasing Complaint `CMP-2026-1001` (or your newly registered complaint).
   - Inspect masked entities (`+91 98****3210`, `f***h@ybl`, `TXN-88421`).
   - Observe **AI/ML Risk Score: 0.87 (HIGH)** with 89% confidence.
   - Click **Bank Lookup** to inspect sender account masking (`XXXX-XXXX-4921`) and bank status (`FLAGGED_SUSPICIOUS`).
   - View the interactive **Leaflet GIS Map** displaying high-risk cash-out spots in Bhubaneswar in red.
   - Click **Verify Prediction** to update verification status.
   - Change investigation status to **Pending Bank Freeze** or **Action Taken**.

---

## 📡 REST API Endpoint Summary

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/auth/register-otp` | Request 6-digit real-time OTP for citizen auth |
| `POST` | `/api/auth/verify-otp` | Verify OTP & receive JWT token for citizen |
| `POST` | `/api/auth/authority-login` | Authenticate with 3 Authority Options (`POLICE`, `CYBER_AUTHORITY`, `BANK_AUTHORITY`) |
| `POST` | `/api/complaints` | Submit new cybercrime complaint (Auto-routes to Cyber Authority) |
| `GET` | `/api/complaints` | List & search complaints with masked entity privacy |
| `GET` | `/api/complaints/{id}` | Detailed complaint view with entity linkage & related cases |
| `PUT` | `/api/complaints/{id}/status` | Update investigation status |
| `GET` | `/api/transactions/{id}` | Fetch bank transaction details (Bank Module REST API) |
| `POST` | `/api/predictions` | Execute ML risk scoring for complaint features |
| `POST` | `/api/predictions/{id}/verify` | Verify or reject AI prediction (Human decision support) |
| `GET` | `/api/risk-locations` | Retrieve high-risk cash-out ATM locations for Leaflet GIS Map |
| `GET` | `/api/alerts` | Retrieve investigator alerts |
| `WS` | `/ws/alerts` | Real-time WebSocket connection for live notification feed |

---

## 🔒 Security & Data Masking Notice
- **Dummy Data Only**: Built exclusively for hackathon demonstration using synthetic test data.
- **Privacy Protection**: PII (Phone numbers, UPI handles, account numbers) are automatically anonymized before rendering on authority screens.
- **Decision-Support AI**: Machine learning outputs are explicit decision-support metrics requiring human verification by authorized officers.
