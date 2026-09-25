import json
import random
from faker import Faker

fake = Faker('en_IN')
Faker.seed(42)
random.seed(42)

# Common shared entities to simulate fraud rings
SHARED_UPI = ["scammer1@upi", "fastcash@ybl", "refunddeal@paytm"]
SHARED_PHONES = ["+919876543210", "+919123456789"]

CRIME_TYPES = ["UPI Fraud", "Phishing", "Shopping Fraud", "Identity Theft"]
CITIES = [
    {"city": "Mumbai", "lat": 19.0760, "lng": 72.8777},
    {"city": "Delhi", "lat": 28.6139, "lng": 77.2090},
    {"city": "Bengaluru", "lat": 12.9716, "lng": 77.5946},
    {"city": "Bhubaneswar", "lat": 20.2961, "lng": 85.8245}
]

complaints = []

for i in range(1, 51):
    loc = random.choice(CITIES)
    # Inject shared entities into 40% of complaints to create links
    if random.random() < 0.4:
        upi = random.choice(SHARED_UPI)
        phone = random.choice(SHARED_PHONES)
    else:
        upi = f"user{i}@{fake.bank().lower().replace(' ', '')}"
        phone = fake.phone_number()

    complaints.append({
        "complaint_id": f"CMP-2026-{i:03d}",
        "description": f"Victim reported an unauthorized transaction via {upi} after receiving a deceptive link.",
        "crime_type": random.choice(CRIME_TYPES),
        "upi_id": upi,
        "phone_number": phone,
        "ip_address": fake.ipv4(),
        "location": loc["city"],
        "latitude": loc["lat"] + random.uniform(-0.05, 0.05),
        "longitude": loc["lng"] + random.uniform(-0.05, 0.05),
        "timestamp": fake.date_time_between(start_date="-30d", end_date="now").isoformat()
    })

with open("mock_data.json", "w") as f:
    json.dump(complaints, f, indent=2)

print("Generated 50 mock complaints in mock_data.json")