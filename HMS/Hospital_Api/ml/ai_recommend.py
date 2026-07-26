from .ai_symptom_checker import AISymptomChecker

ai_checker = AISymptomChecker()

def predict_department(symptom_text):
    results = ai_checker.predict_disease(symptom_text)
    return results[0]["disease"]
