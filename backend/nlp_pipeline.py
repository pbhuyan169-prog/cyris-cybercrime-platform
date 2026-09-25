import os
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline

class CyrisNLPClassifier:
    def __init__(self):
        # Sample training corpus mapping text patterns to fraud types
        training_data = [
            ("Victim reported unauthorized transaction via UPI after scanning QR code", "UPI Fraud"),
            ("Money debited from account using fake Google Pay link", "UPI Fraud"),
            ("Received deceptive phishing link claiming account suspension from bank", "Phishing"),
            ("Fake email asking to verify login credentials immediately", "Phishing"),
            ("Ordered item online on fake e-commerce website but item was never delivered", "Shopping Fraud"),
            ("Paid advance for product on social media marketplace seller blocked victim", "Shopping Fraud"),
            ("Scammer used stolen Aadhaar and PAN details to apply for loan", "Identity Theft"),
            ("Unauthorized SIM swap led to account takeover and profile duplication", "Identity Theft")
        ]

        texts, labels = zip(*training_data)
        
        # Build TF-IDF + Naive Bayes Classification Pipeline
        self.model = make_pipeline(TfidfVectorizer(), MultinomialNB())
        self.model.fit(texts, labels)

    def classify_complaint(self, text: str) -> dict:
        """Predicts the crime category and returns confidence scores."""
        predicted_category = self.model.predict([text])[0]
        probabilities = self.model.predict_proba([text])[0]
        confidence = float(max(probabilities))

        return {
            "predicted_crime_type": predicted_category,
            "confidence_score": round(confidence, 2)
        }

if __name__ == "__main__":
    classifier = CyrisNLPClassifier()
    sample_text = "Received a suspicious link asking to enter UPI PIN to claim reward"
    result = classifier.classify_complaint(sample_text)
    print("NLP Classification Result:")
    print(json.dumps(result, indent=2))