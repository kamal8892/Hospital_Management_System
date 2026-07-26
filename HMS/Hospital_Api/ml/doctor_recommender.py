# Hospital_Api/doctor_recommender.py
import os
from .ai_recommend import predict_department

class DoctorRecommender:

    def __init__(self):
        # Department → Doctor mapping
        self.dept_to_doctor = {
            "General Physician": {
                "name": "Dr. Rajesh Saini",
                "specialization": "General Physician",
                "slot": "11:30 AM"
            },
            "Cardiologist": {
                "name": "Dr. Arvind Saini",
                "specialization": "Cardiologist",
                "slot": "09:30 AM"
            },
            "Dermatologist": {
                "name": "Dr. Punita Soni",
                "specialization": "Dermatologist",
                "slot": "12:00 PM"
            },
            "Orthopedic": {
                "name": "Dr. Akshya Nigam",
                "specialization": "Orthopedic Surgeon",
                "slot": "12:45 PM"
            },
            "Gastroenterologist": {
                "name": "Dr. Suresh Gupta",
                "specialization": "Gastroenterologist",
                "slot": "02:30 PM"
            },
            "Psychiatrist": {
                "name": "Dr. Neha Saini",
                "specialization": "Psychiatrist",
                "slot": "11:15 AM"
            },
            "Ophthalmologist": {
                "name": "Dr. Puskar Kumar",
                "specialization": "Ophthalmologist",
                "slot": "10:45 AM"
            }
        }

    def recommend(self, symptoms, age):
        # 1. Predict department
        department = predict_department(symptoms)

        # 2. Get doctor for this department
        doctor = self.dept_to_doctor.get(department)

        if doctor:
            return doctor
        
        # fallback
        return {
            "name": "Dr. Temporary Model",
            "specialization": "General",
            "slot": "11:00 AM (Dummy)"
        }










# import joblib
# import numpy as np
# import os

# class DoctorRecommender:

#     def __init__(self):
#         model_path = os.path.join("Hospital_Api", "ml", "model.pkl")

#         try:
#             self.model = joblib.load(model_path)
#         except:
#             self.model = None

#         self.doctors = {
#             0: {"name": "Dr. Rajesh Saini", "specialization": "Cardiologist", "slot": "11:30 AM"},
#             1: {"name": "Dr. Puskar Kumar", "specialization": "General Surgery", "slot": "02:00 PM"},
#             2: {"name": "Dr. Akshya Nigam", "specialization": "Orthopedic Surgery", "slot": "12:45 PM"},
#             3: {"name": "Dr. Neha Saini", "specialization": "Neurology", "slot": "10:45 AM"},
#             4: {"name": "Dr. Arvind Saini", "specialization": "Cardiologist", "slot": "09:30 AM"},
#             5: {"name": "Dr. Punita Soni", "specialization": "Brain Specialist", "slot": "11:00 AM"},
#         }

#     def recommend(self, symptoms, age):

#         # MODEL NOT LOADED → fallback
#         if not self.model:
#             return {
#                 "name": "Dr. Temporary Model",
#                 "specialization": "General",
#                 "slot": "11:00 AM (Dummy)"
#             }

#         x = np.array([[age, len(symptoms)]])
#         prediction = self.model.predict(x)[0]

#         doctor = self.doctors.get(prediction)

#         # If prediction invalid → fallback
#         if not doctor:
#             return {
#                 "name": "Dr. Temporary Model",
#                 "specialization": "General",
#                 "slot": "11:00 AM (Fallback)"
#             }

#         return doctor
