import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline

def train_and_save_model():
    print("Training Cybercrime Risk Model...")
    
    # Generate synthetic training dataset
    np.random.seed(42)
    n_samples = 1000

    fraud_types = ["UPI_FRAUD", "BANKING_FRAUD", "ATM_FRAUD", "PHISHING", "SOCIAL_MEDIA_SCAM", "ONLINE_SHOPPING"]
    age_groups = ["18-25", "26-40", "41-60", "60+"]

    data = {
        "fraud_type": np.random.choice(fraud_types, size=n_samples),
        "amount": np.random.exponential(scale=20000, size=n_samples) + 500,
        "hour_of_day": np.random.randint(0, 24, size=n_samples),
        "victim_age_group": np.random.choice(age_groups, size=n_samples),
        "device_risk": np.random.uniform(1.0, 10.0, size=n_samples),
        "location_risk": np.random.uniform(1.0, 10.0, size=n_samples),
        "previous_complaints": np.random.poisson(lam=1.5, size=n_samples),
    }

    df = pd.DataFrame(data)

    # Risk calculation heuristic for synthetic labels
    def assign_risk_label(row):
        score = 0.0
        if row["amount"] > 20000: score += 0.3
        elif row["amount"] > 10000: score += 0.15
        
        if row["fraud_type"] in ["UPI_FRAUD", "ATM_FRAUD", "BANKING_FRAUD"]: score += 0.25
        if row["hour_of_day"] in [23, 0, 1, 2, 3, 4]: score += 0.20
        if row["device_risk"] > 6.0: score += 0.15
        if row["previous_complaints"] > 2: score += 0.15

        if score >= 0.60:
            return "HIGH"
        elif score >= 0.35:
            return "MEDIUM"
        else:
            return "LOW"

    df["risk_level"] = df.apply(assign_risk_label, axis=1)

    X = df[["fraud_type", "amount", "hour_of_day", "victim_age_group", "device_risk", "location_risk", "previous_complaints"]]
    y = df["risk_level"]

    categorical_features = ["fraud_type", "victim_age_group"]
    numerical_features = ["amount", "hour_of_day", "device_risk", "location_risk", "previous_complaints"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), categorical_features),
            ("num", "passthrough", numerical_features),
        ]
    )

    pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", RandomForestClassifier(n_estimators=100, random_state=42)),
        ]
    )

    pipeline.fit(X, y)

    # Target directory
    ml_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(ml_dir, exist_ok=True)
    model_path = os.path.join(ml_dir, "cyris_risk_model.pkl")

    joblib.dump(pipeline, model_path)
    print(f"Model saved successfully to {model_path}")
    return model_path

if __name__ == "__main__":
    train_and_save_model()
