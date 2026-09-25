import os
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.database import engine, Base, SessionLocal
from backend.app.models import User, Complaint, Transaction, Location, Prediction, Alert, RelatedCase
from backend.app.security import hash_password, mask_account, mask_upi

def seed_database():
    print("Re-creating Database Tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("Seeding Authority Users...")
        # 1. Authority Users
        police = User(
            username="police_officer",
            email="police.investigator@cyris.gov.in",
            phone="+919876500001",
            hashed_password=hash_password("admin123"),
            role="POLICE",
            authority_type="POLICE"
        )
        cyber = User(
            username="cyber_authority",
            email="cyber.cell@cyris.gov.in",
            phone="+919876500002",
            hashed_password=hash_password("admin123"),
            role="CYBER_AUTHORITY",
            authority_type="CYBER_AUTHORITY"
        )
        bank = User(
            username="bank_officer",
            email="bank.nodal@cyris.gov.in",
            phone="+919876500003",
            hashed_password=hash_password("admin123"),
            role="BANK_AUTHORITY",
            authority_type="BANK_AUTHORITY"
        )
        db.add_all([police, cyber, bank])
        db.commit()

        print("Seeding GIS High-Risk Cash-Out Locations...")
        # 2. GIS Cash-out locations
        loc1 = Location(
            name="SBI ATM - Master Canteen Square",
            city="Bhubaneswar",
            state="Odisha",
            latitude=20.2961,
            longitude=85.8245,
            risk_level="HIGH",
            related_cases_count=8,
            suspicious_tx_count=18,
            last_tx_time="10 mins ago"
        )
        loc2 = Location(
            name="HDFC ATM - Patia Square",
            city="Bhubaneswar",
            state="Odisha",
            latitude=20.3548,
            longitude=85.8153,
            risk_level="HIGH",
            related_cases_count=5,
            suspicious_tx_count=12,
            last_tx_time="25 mins ago"
        )
        loc3 = Location(
            name="ICICI ATM - Saheed Nagar",
            city="Bhubaneswar",
            state="Odisha",
            latitude=20.2882,
            longitude=85.8436,
            risk_level="MEDIUM",
            related_cases_count=3,
            suspicious_tx_count=6,
            last_tx_time="1 hour ago"
        )
        loc4 = Location(
            name="Axis Bank ATM - Khandagiri",
            city="Bhubaneswar",
            state="Odisha",
            latitude=20.2577,
            longitude=85.7831,
            risk_level="LOW",
            related_cases_count=1,
            suspicious_tx_count=2,
            last_tx_time="3 hours ago"
        )
        db.add_all([loc1, loc2, loc3, loc4])
        db.commit()

        print("Seeding Demonstration Case CMP-2026-1001...")
        # 3. Explicit Demonstration Case
        demo_complaint = Complaint(
            complaint_id="CMP-2026-1001",
            full_name="Rajesh Mohanty",
            phone_number="+919876543210",
            email="rajesh.m@gmail.com",
            fraud_type="UPI_FRAUD",
            transaction_id="TXN-88421",
            amount=25000.0,
            upi_id="fastcash.refund@ybl",
            city="Bhubaneswar",
            state="Odisha",
            latitude=20.2961,
            longitude=85.8245,
            description="Victim was tricked into clicking a phishing refund link on WhatsApp. Unauthorised debit of ₹25,000 occurred via UPI to fastcash.refund@ybl.",
            status="Under Review",
            assigned_authority="CYBER_AUTHORITY"
        )
        db.add(demo_complaint)
        db.commit()

        # Mock transaction for demonstration case
        demo_tx = Transaction(
            transaction_id="TXN-88421",
            sender_account_masked=mask_account("624910844921"),
            receiver_upi="fastcash.refund@ybl",
            amount=25000.0,
            timestamp=datetime.now(timezone.utc) - timedelta(minutes=15),
            tx_type="UPI_TRANSFER",
            atm_location="SBI ATM - Master Canteen Square, Bhubaneswar",
            latitude=20.2961,
            longitude=85.8245,
            status="FLAGGED_SUSPICIOUS"
        )
        db.add(demo_tx)
        db.commit()

        # Prediction for demo case
        demo_pred = Prediction(
            complaint_id="CMP-2026-1001",
            risk_score=0.87,
            risk_level="HIGH",
            confidence=0.89,
            status="Pending Verification"
        )
        db.add(demo_pred)

        # Alert for demo case
        demo_alert = Alert(
            complaint_id="CMP-2026-1001",
            risk_score=0.87,
            location_name="SBI ATM - Master Canteen Square",
            reason="High-Risk UPI_FRAUD pattern detected (₹25,000.00)",
            verification_status="Pending"
        )
        db.add(demo_alert)
        db.commit()

        print("Seeding Additional 15 Dummy Complaints & Transactions...")
        dummy_data = [
            ("CMP-2026-1002", "Ananya Mishra", "+919123456789", "ONLINE_BANKING_FRAUD", "TXN-77312", 48000.0, "scammer.pay@paytm", 20.3548, 85.8153, 0.82, "HIGH"),
            ("CMP-2026-1003", "Amit Kumar", "+919876512345", "ATM_FRAUD", "TXN-66104", 12000.0, "cashout@icici", 20.2882, 85.8436, 0.65, "MEDIUM"),
            ("CMP-2026-1004", "Pooja Das", "+919988776655", "PHISHING", "TXN-55912", 5000.0, "verify.link@upi", 20.2577, 85.7831, 0.35, "LOW"),
            ("CMP-2026-1005", "Suresh Rout", "+919437012345", "SOCIAL_MEDIA_SCAM", "TXN-44810", 15000.0, "deal.seller@okaxis", 20.2961, 85.8245, 0.72, "HIGH"),
            ("CMP-2026-1006", "Smita Patnaik", "+919861054321", "ONLINE_SHOPPING", "TXN-33290", 8500.0, "shopdeal@ybl", 20.3548, 85.8153, 0.45, "MEDIUM"),
            ("CMP-2026-1007", "Manas Jena", "+919937182736", "UPI_FRAUD", "TXN-22109", 32000.0, "fastcash.refund@ybl", 20.2961, 85.8245, 0.88, "HIGH"), # Related to demo!
            ("CMP-2026-1008", "Deepak Swain", "+919777123987", "ATM_FRAUD", "TXN-11088", 20000.0, "atm.cash@sbi", 20.2882, 85.8436, 0.68, "MEDIUM"),
            ("CMP-2026-1009", "Pravat Nayak", "+919438901234", "PHISHING", "TXN-99801", 3500.0, "lottery.win@paytm", 20.2577, 85.7831, 0.28, "LOW"),
            ("CMP-2026-1010", "Subhashree Roy", "+919853198765", "UPI_FRAUD", "TXN-88762", 60000.0, "crypto.invest@ybl", 20.3548, 85.8153, 0.94, "HIGH")
        ]

        for cid, name, phone, ftype, txid, amt, upi, lat, lng, score, rlevel in dummy_data:
            c_obj = Complaint(
                complaint_id=cid,
                full_name=name,
                phone_number=phone,
                email=f"{name.lower().replace(' ', '.')}@example.com",
                fraud_type=ftype,
                transaction_id=txid,
                amount=amt,
                upi_id=upi,
                city="Bhubaneswar",
                state="Odisha",
                latitude=lat,
                longitude=lng,
                description=f"Automated incident report for suspicious {ftype} involving {upi}.",
                status="Under Review",
                assigned_authority="CYBER_AUTHORITY"
            )
            db.add(c_obj)
            
            p_obj = Prediction(
                complaint_id=cid,
                risk_score=score,
                risk_level=rlevel,
                confidence=0.86,
                status="Pending Verification"
            )
            db.add(p_obj)
            
            if score >= 0.70:
                a_obj = Alert(
                    complaint_id=cid,
                    risk_score=score,
                    location_name="Bhubaneswar Cash-Out ATM",
                    reason=f"High-Risk {ftype} anomaly score {score}",
                    verification_status="Pending"
                )
                db.add(a_obj)

        # Related case link between demo case CMP-2026-1001 and CMP-2026-1007
        rc = RelatedCase(
            complaint_id_1="CMP-2026-1001",
            complaint_id_2="CMP-2026-1007",
            similarity_reason="Matched Receiver UPI ID (fastcash.refund@ybl)",
            similarity_score=0.96
        )
        db.add(rc)
        
        db.commit()
        print("Database Seed Completed Successfully! Ready for Demo Scenario.")

    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
