import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import CountVectorizer
import joblib
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

data = {
    "symptoms": [
        "fever cough weakness",
        "heart pain chest pressure",
        "skin allergy rash",
        "bone pain fracture",
        "fever headache",
        "stomach pain gas acidity",
        "depression anxiety",
        "eye infection irritation",
    ],

    "department": [
        "General Physician",
        "Cardiologist",
        "Dermatologist",
        "Orthopedic",
        "General Physician",
        "Gastroenterologist",
        "Psychiatrist",
        "Ophthalmologist"
    ]
}

df = pd.DataFrame(data)

# Encode department
le = LabelEncoder()
df["department_encoded"] = le.fit_transform(df["department"])

# Split
X_train, X_test, y_train, y_test = train_test_split(
    df["symptoms"], df["department_encoded"], test_size=0.2
)

# Vectorizer
cv = CountVectorizer()
X_train_cv = cv.fit_transform(X_train)

# Train model
model = RandomForestClassifier()
model.fit(X_train_cv, y_train)

# Save files
joblib.dump(model, os.path.join(BASE_DIR, "doctor_model.pkl"))
joblib.dump(cv, os.path.join(BASE_DIR, "vectorizer.pkl"))
joblib.dump(le, os.path.join(BASE_DIR, "labelencoder.pkl"))

print("Model trained and saved successfully!")
