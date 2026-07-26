import random
from Hospital_Api.models import OTPVerification
from Hospital_Api.tasks import send_otp_email
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import render
from Hospital_Api.serializers import (H_UserSerializer,
    DoctorSerializer,
    PatientSerializer,
    AppointmentSerializer,
    MedicalRecordSerializer,
    MedicineSerializer,
    BillingSerializer,
    RoomSerializer,
    PatientRoomAdmissionSerializer,
    LabTestSerializer,
    LabTestRequestSerializer,
    LabResultSerializer,
    NurseStaffSerializer,
    NurseDutyLogSerializer,
    PaymentSerializer
)
from rest_framework import status,permissions,viewsets
from Hospital_Api.models import *
from rest_framework.response import Response
from rest_framework.decorators import api_view,APIView
from django.http.response import JsonResponse
from django.contrib.auth.hashers import make_password,check_password
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
import json
import re 
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from django.utils import timezone
from django.utils.timezone import now
from datetime import timedelta,datetime
from rest_framework import status
from django.utils.timezone import make_aware
import decimal
from Hospital_Api.ml.doctor_recommender import DoctorRecommender
from Hospital_Api.ml.ai_recommend import predict_department
from Hospital_Api.ml.ai_symptom_checker import AISymptomChecker

symptom_ai = AISymptomChecker()

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
import uuid

from Hospital_Api.models import PasswordResetOTP
from django.contrib.auth import update_session_auth_hash
from rest_framework.permissions import IsAuthenticated


User = get_user_model()



# Hospital User Signup Api

@api_view(['POST'])
def H_User_Signup(request):
    First_name = request.data.get('First_name')
    Last_name = request.data.get('Last_name')
    city = request.data.get('city')
    phone = request.data.get('phone')
    email = request.data.get('email')
    password = request.data.get('password')

    if not First_name or not Last_name or not email or not password:
        return Response({'msg':'Missing Required fields'},status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email=email).exists():
        return Response({'error': 'User already exists'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.create_user(
        username=email,
        first_name=First_name,
        last_name=Last_name,
        email=email,
        password=password
    )

    H_Users.objects.create(
        First_name=First_name,
        Last_name=Last_name,
        city=city,
        email=email,
        phone=phone,
        password=make_password(password)
    )

    refresh = RefreshToken.for_user(user)

    return Response({
        "success": True,
        "message": "User created successfully.",
        "refresh": str(refresh),
        "access": str(refresh.access_token)
    }, status=status.HTTP_201_CREATED)


def signup_page(request):
    return render(request, "signup.html", {'GOOGLE_OAUTH_CLIENT_ID': settings.GOOGLE_OAUTH_CLIENT_ID})


@api_view(['POST'])
def Login(request):
    if request.method == 'POST':
        email = request.data.get('email')
        password = request.data.get('password')

        if not email and not password:
            return Response({'msg':'Email and password are not correct'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            huser = User.objects.get(email=email)
        except H_Users.DoesNotExist:
            return Response({'msg':'Invalid email and password'},status=status.HTTP_400_BAD_REQUEST)
        if huser.check_password(password):
            refresh = RefreshToken.for_user(huser)  
            access_token = refresh.access_token
            print("USer login successfully and token are created")

            return JsonResponse({
                'refresh': str(refresh),
                'access': str(access_token),
                "success": "Login successfully",
                "user": {
                "id": huser.id,
                "first_name": huser.first_name,
                "last_name": huser.last_name,
                "email": huser.email
                }
            }, status=status.HTTP_200_OK)

        return JsonResponse({'msg': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

def book_appointment(request):
    return render(request, "appointments_form.html")


    
@api_view(['POST'])
def Logout(request):
    try:
        refresh_token = request.data.get("refresh")

        if refresh_token is None:
            return Response({"msg": "Refresh token not provided"}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()  

        return Response({"success": True, "msg": "Logout successful"}, status=200)

    except Exception as e:
        return Response({"msg": "Invalid token"}, status=400)


class GoogleLoginApi(APIView):
    def post(self, request):
        token = request.data.get('id_token')
        if not token:
            return Response({"error": "No token provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), settings.GOOGLE_OAUTH_CLIENT_ID)

            email = idinfo.get('email')
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')

            if not email:
                return Response({"error": "Email not found in token"}, status=status.HTTP_400_BAD_REQUEST)

            user, created = User.objects.get_or_create(email=email, defaults={
                'username': email,
                'first_name': first_name,
                'last_name': last_name,
            })

            if created:
                user.set_unusable_password()
                user.save()

                H_Users.objects.create(
                    First_name=first_name,
                    Last_name=last_name,
                    email=email,
                    password=make_password(None)
                )

            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token

            return JsonResponse({
                'refresh': str(refresh),
                'access': str(access_token),
                "success": "Login successfully",
                "user": {
                    "id": user.id,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "email": user.email
                }
            }, status=status.HTTP_200_OK)

        except ValueError:
            return Response({"error": "Invalid token"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    
@api_view(['GET'])
def get_user(request, pk):
    try:
        user = User.objects.get(id=pk)
        return Response({
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email
        })
    except User.DoesNotExist:
        return Response({"error": "User not found"}, status=404)

    

def login_page(request):
    return render(request, "login.html", {'GOOGLE_OAUTH_CLIENT_ID': settings.GOOGLE_OAUTH_CLIENT_ID})

def logout_page(request):
    return render(request, "logout.html")


def dashboard_page(request):
    return render(request, "dashboard.html")

# Apply Permission class Method only admin can allow add and delete and any modification 

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'admin'
    

class AIRecommendationAPI(APIView):
    def post(self, request):
        symptoms = request.data.get("symptoms", "")
        age = int(request.data.get("age", 0))

        recommender = DoctorRecommender()
        result = recommender.recommend(symptoms, age)

        return Response({
            "recommended_doctor": result["name"],
            "specialization": result["specialization"],
            "best_slot": result["slot"]
        })


@csrf_exempt

@api_view(["POST"])
def ai_symptom_checker(request):
    symptoms = request.data.get("symptoms")

    if not symptoms:
        return Response({"error": "Symptoms required"}, status=400)

    result = symptom_ai.predict_disease(symptoms)

    return Response({
        "analysis": result
    })





class VoiceAssistantAPI(APIView):

    def post(self, request):
        text = request.data.get("query", "").lower()

        # --- 1) BOOK APPOINTMENT LOGIC ---
        if "book" in text and "appointment" in text:
            doctor = None
            time = None

            # doctor extract
            match = re.search(r"with (.*?) at", text)
            if match:
                doctor = match.group(1)

            # time extract
            match = re.search(r"at ([0-9]+\s?(am|pm))", text)
            if match:
                time = match.group(1)

            if doctor and time:
                return Response({
                    "response": f"Okay! Booking an appointment with {doctor} at {time}."
                })

            return Response({"response": "Which doctor and time should I book?"})

        # --- 2) SYMPTOM CHECKER LOGIC ---
        if "fever" in text or "pain" in text or "cough" in text:
            result = symptom_ai.predict_disease(text)
            disease = result[0]["disease"]
            medicine = result[0]["medicine"]
            return Response({
                "response": f"It looks like {disease}. Suggested medicine: {medicine}."
            })

        # --- 3) SHOW DOCTORS ---
        if "show doctors" in text:
            return Response({
                "response": "Available doctors: Dentist, Cardiologist, Neurologist, Dermatologist."
            })

        # --- DEFAULT ---
        return Response({
            "response": "Sorry, I didn’t understand. You can say: Book appointment, I have fever, Show doctors etc."
        })








@api_view(["POST"])
def ai_recommend_doctor(request):
    symptoms = request.data.get("symptoms", "")

    if symptoms == "":
        return Response({"error": "Symptoms required"}, status=400)

    # 1️⃣ GET BEST DEPARTMENT FROM AI
    best_department = predict_department(symptoms)

    # 2️⃣ FIND DOCTORS WITH SAME DEPARTMENT
    doctors = Doctor.objects.filter(specialization__icontains=best_department)

    if doctors.exists():
        doc = doctors.first()
        return Response({
            "recommended_department": best_department,
            "doctor_name": doc.full_name,
            "experience": doc.experience_years,
            "next_available_slot": "11:30 AM",
            "message": f"Based on symptoms → {doc.full_name} is a good match."
        })
    else:
        return Response({
            "recommended_department": best_department,
            "doctor_name": None,
            "message": "No doctor found for this department!"
        })


# Doctor APi Apply All Business Logic


@api_view(['POST'])
def doctor_signup(request):
    full_name = request.data.get('full_name')
    specialization = request.data.get('specialization')
    experience_years = request.data.get('experience_years', 0)
    consultation_fee = request.data.get('consultation_fee', 0)
    available_from = request.data.get('available_from')
    available_to = request.data.get('available_to')

    email = request.data.get('email')
    phone = request.data.get('phone')
    password = request.data.get('password')
    city = request.data.get('city')

    if not full_name or not specialization or not email or not password:
        return Response({'msg': 'Missing Required Fields'}, status=status.HTTP_400_BAD_REQUEST)

    # Check duplicate users
    if H_Users.objects.filter(email=email).exists():
        return Response({'msg': 'User already exists with this email'}, status=status.HTTP_400_BAD_REQUEST)

    # Create user in H_Users
    user = H_Users.objects.create(
        First_name=full_name,
        Last_name="",
        city=city,
        phone=phone,
        email=email,
        password=make_password(password)
    )

    # Create Doctor linked to H_Users
    doctor = Doctor.objects.create(
        user=user,
        full_name=full_name,
        specialization=specialization,
        experience_years=experience_years,
        consultation_fee=consultation_fee,
        available_from=available_from,
        available_to=available_to
    )

    # JWT Token
    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token

    return Response({
        "msg": "Doctor Registered Successfully",
        "doctor_id": doctor.id,
        "access_token": str(access_token),
        "refresh_token": str(refresh)
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
def doctor_login(request):
    email = request.data.get('email')
    password = request.data.get('password')

    try:
        user = H_Users.objects.get(email=email)
    except H_Users.DoesNotExist:
        return Response({"msg": "Invalid Credentials"}, status=status.HTTP_400_BAD_REQUEST)

    if not check_password(password, user.password):
        return Response({"msg": "Invalid Password"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        doctor = Doctor.objects.get(user=user)
    except Doctor.DoesNotExist:
        return Response({"msg": "Doctor Profile Not Found"}, status=status.HTTP_404_NOT_FOUND)

    refresh = RefreshToken.for_user(user)
    access_token = refresh.access_token

    return Response({
        "msg": "Login Successful",
        "doctor_id": doctor.id,
        "access_token": str(access_token),
        "refresh_token": str(refresh)
    }, status=status.HTTP_200_OK)


# Doctor Api Apply All Business logic and CURD Method


@api_view(['GET'])
def doctor_count(request):
    total = Doctor.objects.count()
    return Response({"total_doctors": total})

@api_view(['GET'])
def doctor_list(request):
    doctors = Doctor.objects.all()
    
    data = []
    for d in doctors:
        data.append({
            "id": d.id,
            "full_name": d.full_name,
            "specialization": d.specialization,
            "email": d.user.email if d.user else "",
            "photo": request.build_absolute_uri(d.photo.url) if d.photo else "",
            "experience_years": d.experience_years,
            "consultation_fee": str(d.consultation_fee),
        })

    return Response(data)

def doctor_page(request):
    return render(request, "doctor.html")



@api_view(['GET'])

def Doctor_list(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                dctr = Doctor.objects.get(id=pk)
            except Doctor.DoesNotExist:
                return Response({'msg':'User id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = DoctorSerializer(dctr)
            return Response(serializer.data)
        
@api_view(['GET'])   
def doctor_list(request):    

    dctr = Doctor.objects.all()
    serializer = DoctorSerializer(dctr,many=True)
    return Response(serializer.data)
    

@api_view(['POST'])

def Doctor_Create_Api(request):
    full_name = request.data.get('full_name')
    specialization = request.data.get('specialization')
    experience_years = request.data.get('experience_years')
    consultation_fee = request.data.get('consultation_fee')
    available_from = request.data.get('available_from')
    available_to = request.data.get('available_to')
    email = request.data.get('email')
    phone = request.data.get('phone')
    city = request.data.get('city')
    password = request.data.get('password')
    photo = request.FILES.get('photo')

    if not full_name or not email or not password or not specialization:
        return JsonResponse({'msg':'Missing Required fileds'},status=status.HTTP_400_BAD_REQUEST)
    
    if H_Users.objects.filter(email=email).exists():
        return Response({"msg": "Doctor already registered with this email"}, status=status.HTTP_400_BAD_REQUEST)
    
    if float (consultation_fee) < 0:
        return Response({'msg':'Fees can not be negative'},status=status.HTTP_400_BAD_REQUEST)
    if int (experience_years) < 0:
        return Response({'msg':'Experience can not be zero ya negative'},status=status.HTTP_400_BAD_REQUEST)
    
    if available_from >= available_to:
        return Response({'msg':'Available time range invalid'},status=status.HTTP_400_BAD_REQUEST)
    

    user = H_Users.objects.create(
        First_name=full_name,
        Last_name="",
        city=city,
        phone=phone,
        email=email,
        password=make_password(password)
    )

    # Create Doctor linked to H_Users
    doctor = Doctor.objects.create(
        user=user,
        full_name=full_name,
        specialization=specialization,
        experience_years=experience_years,
        consultation_fee=consultation_fee,
        available_from=available_from,
        available_to=available_to,
        photo = photo
    )
    return Response({'msg':'Doctor Registration Successfully',"doctor_id":doctor.id},status=status.HTTP_201_CREATED)

# selected_doctor = request.POST["doctor"]



@api_view(['PUT'])
def doctor_update_Api(request, pk):

    try:
        doctor = Doctor.objects.get(id=pk)
    except Doctor.DoesNotExist:
        return Response({"msg": "Doctor Not Found"}, status=status.HTTP_404_NOT_FOUND)

    user = doctor.user

    # GET DATA
    full_name = request.data.get('full_name', doctor.full_name)
    specialization = request.data.get('specialization', doctor.specialization)
    experience_years = request.data.get('experience_years', doctor.experience_years)
    consultation_fee = request.data.get('consultation_fee', doctor.consultation_fee)
    available_from = request.data.get('available_from', doctor.available_from)
    available_to = request.data.get('available_to', doctor.available_to)
    phone = request.data.get('phone', user.phone)
    city = request.data.get('city', user.city)
    photo = request.FILES.get('photo')   # NEW PHOTO

    # VALIDATIONS
    if int(experience_years) < 0:
        return Response({"msg": "Experience cannot be negative"}, status=400)

    if float(consultation_fee) < 0:
        return Response({"msg": "Fee cannot be negative"}, status=400)

    if available_from >= available_to:
        return Response({"msg": "Available time range invalid"}, status=400)

    # UPDATE USER
    user.First_name = full_name
    user.phone = phone
    user.city = city
    user.save()

    # UPDATE DOCTOR
    doctor.full_name = full_name
    doctor.specialization = specialization
    doctor.experience_years = experience_years
    doctor.consultation_fee = consultation_fee
    doctor.available_from = available_from
    doctor.available_to = available_to

    # IMPORTANT: Update photo only if user uploaded a new one
    if photo:
        doctor.photo = photo

    doctor.save()

    return Response({"msg": "Doctor Updated Successfully"}, status=200)


@api_view(['DELETE'])

def Doctor_delete_APi(request,pk):
    if request.method == 'DELETE':
        try:
            doctor = Doctor.objects.get(id=pk)
        except Doctor.DoesNotExist:
            return Response({'msg':'Doctor id not found '},status=status.HTTP_404_NOT_FOUND)
        user = doctor.user
        doctor.delete()
        user.delete()
        return Response({'msg':'Doctor deleted successfully'},status=status.HTTP_200_OK)
    


# Patient APi and apply all business logic and curd method

@api_view(['GET'])
def patient_count(request):
    total = Patient.objects.count()
    return Response({"total_patients": total})



@api_view(['GET'])

def Patient_list(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                patient = Patient.objects.get(id=pk)
            except Patient.DoesNotExist:
                return Response({'msg':'Patient id not correct'},status=status.HTTP_400_BAD_REQUEST)
            serializer = PatientSerializer(patient)
            return Response(serializer.data)
        
        
@api_view(['GET'])
def patient_Api(request):
        if request.method =='GET':
            patient = Patient.objects.all()
            serializer = PatientSerializer(patient,many=True)
            return Response(serializer.data)
    

def patients_page(request):
    return render(request, "patients.html")


@api_view(['POST'])

def Patient_Create_Api(request):
    if request.method == 'POST':
        full_name = request.data.get('full_name')
        age = request.data.get('age')
        gender = request.data.get('gender')
        blood_group = request.data.get('blood_group')
        address = request.data.get('address')
        emergency_contact = request.data.get('emergency_contact')
        registration_date = request.data.get('registration_date')


        if not full_name or not blood_group or not address or not emergency_contact:
            return Response({'msg':'Missing Required fields'},status=status.HTTP_400_BAD_REQUEST)
        
        if age:
            try:
                age = int(age)
                if age <=0:
                    return Response({'msg':'AGe can not be negative'},status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({'msg':'Age must be positive'},status=status.HTTP_400_BAD_REQUEST)
            

            valid_gender = ['Male','Female','Other']
            if gender and gender not in valid_gender:
                return Response({'msg':f'gender must be one of {valid_gender}'},status=status.HTTP_400_BAD_REQUEST)
            
            if not (emergency_contact.isdigit() and len (emergency_contact) ==10):
                return Response({'msg':'Emergency_contact must be 10 number'},status=status.HTTP_400_BAD_REQUEST)
            
            if not registration_date:
                registration_date = now().date()
                

            patient = Patient.objects.create(
                full_name = full_name,
                age = age,
                gender = gender,
                blood_group = blood_group,
                address = address,
                emergency_contact = emergency_contact,
                registration_date = registration_date
            )

            serializer = PatientSerializer(patient)
            return Response(serializer.data,status=status.HTTP_201_CREATED)
        

@api_view(['PUT'])

def Patient_Update(request,pk):
    if request.method == 'PUT':
        try:
            patient = Patient.objects.get(id=pk)
        except Patient.DoesNotExist:
            return Response({"msg": "Patient not found"}, status=status.HTTP_404_NOT_FOUND)

    # 2. Update only provided fields
        full_name = request.data.get('full_name', patient.full_name)
        age = request.data.get('age', patient.age)
        gender = request.data.get('gender', patient.gender)
        blood_group = request.data.get('blood_group', patient.blood_group)
        address = request.data.get('address', patient.address)
        emergency_contact = request.data.get('emergency_contact', patient.emergency_contact)


    # Age check only if user passed age in request
        if 'age' in request.data:
            try:
                age = int(age)
                if age <= 0:
                    return Response({'msg': 'Age must be positive'}, status=status.HTTP_400_BAD_REQUEST)
            except:
                return Response({'msg': 'Age must be a number'}, status=status.HTTP_400_BAD_REQUEST)

    # Gender Validate only if provided
            if 'gender' in request.data:
                valid_genders = ["Male", "Female", "Other"]
                if gender not in valid_genders:
                    return Response({'msg': f"Gender must be one of {valid_genders}"}, status=status.HTTP_400_BAD_REQUEST)

    # Blood Group Validate only if provided
            if 'blood_group' in request.data:
                valid_blood_groups = ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]
                if blood_group not in valid_blood_groups:
                    return Response({'msg': f"Blood group must be one of {valid_blood_groups}"}, status=status.HTTP_400_BAD_REQUEST)

    # Emergency Contact Validate only if provided
            if 'emergency_contact' in request.data:
                if not emergency_contact.isdigit() or len(emergency_contact) != 10:
                    return Response({'msg': 'Emergency contact must be a 10 digit number'}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Save updated data
            patient.full_name = full_name
            patient.age = age
            patient.gender = gender
            patient.blood_group = blood_group
            patient.address = address
            patient.emergency_contact = emergency_contact
            patient.save()

            serializer = PatientSerializer(patient)
            return Response({"msg": "Patient updated successfully", "updated_data": serializer.data}, status=status.HTTP_200_OK)
        
@api_view(['DELETE'])

def Patient_delete_APi(request,pk):
    if request.method == 'DELETE':
        try:
            patient = Patient.objects.get(id=pk)
        except Patient.DoesNotExist:
            return Response({'msg':'Patient id not found '},status=status.HTTP_404_NOT_FOUND)
        user = patient.user
        patient.delete()
        user.delete()
        return Response({'msg':'Patient deleted successfully'},status=status.HTTP_200_OK)
    
# ********************** Appointment Api ************************

@api_view(['GET'])
def appointment_count(request):
    total = Appointment.objects.count()
    return Response({"total_appointments": total})



@api_view(['GET'])

def Appointment_list(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                appoit = Appointment.objects.get(id=pk)
            except Appointment.DoesNotExist:
                return Response({'msg':'Appointment id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = AppointmentSerializer(appoit)
            return Response(serializer.data)
    

        
@api_view(['GET'])
def Appoitment_list_Api(request):
    appointments = Appointment.objects.all()
    serializer = AppointmentSerializer(appointments, many=True)
    return Response(serializer.data)    
    
@api_view(['GET'])
def appointments_page(request):
    return render(request, "appointments.html")


@api_view(['POST'])
def Appointment_Create_Api(request):
    doctor_id = request.data.get('doctor')
    patient_id = request.data.get('patient')
    appointment_date = request.data.get('appointment_date')  
    appointment_status = request.data.get('status', 'pending')
    issue_description = request.data.get('issue_description')

    
    if not doctor_id or not patient_id or not appointment_date or not issue_description:
        return Response({"msg": "Missing required fields"}, status=status.HTTP_400_BAD_REQUEST)

    
    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        return Response({"msg": "Doctor does not exist"}, status=status.HTTP_404_NOT_FOUND)

    
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"msg": "Patient does not exist"}, status=status.HTTP_404_NOT_FOUND)

    
    try:
        
        if len(appointment_date) == 10:
            appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d")
           
            appointment_date = appointment_date.replace(hour=10, minute=0)

        else:  
            appointment_date = datetime.fromisoformat(appointment_date)

        
        if appointment_date.tzinfo is None:
            appointment_date = make_aware(appointment_date)

    except:
        return Response({"msg": "Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"},
                        status=status.HTTP_400_BAD_REQUEST)

    
    if appointment_date <= now():
        return Response({"msg": "Appointment date must be in the future"},
                        status=status.HTTP_400_BAD_REQUEST)

    
    if appointment_status not in ['pending', 'completed', 'cancelled']:
        return Response({"msg": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

    
    Appointment.objects.create(
        doctor=doctor,
        patient=patient,
        appointment_date=appointment_date,
        status=appointment_status,
        issue_description=issue_description
    )

    return Response({"msg": "Appointment Created Successfully"}, status=status.HTTP_201_CREATED)


# **************** Appointments Update Api ******************** 

@api_view(['PUT'])
def Appointment_Update_Api(request, pk):
    try:
        # ✅ Check appointment exists
        appointment = Appointment.objects.get(id=pk)
    except Appointment.DoesNotExist:
        return Response({'msg': 'Appointment ID not found'}, status=status.HTTP_404_NOT_FOUND)

    # ✅ Extract updated fields (if not provided, use old values)
    doctor_id = request.data.get('doctor', appointment.doctor_id)
    patient_id = request.data.get('patient', appointment.patient_id)
    appointment_date = request.data.get('appointment_date', appointment.appointment_date)
    appointment_status = request.data.get('status', appointment.status)
    issue_description = request.data.get('issue_description', appointment.issue_description)

    # ✅ Validate doctor and patient IDs (optional but safer)
    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'msg': 'Doctor does not exist'}, status=status.HTTP_404_NOT_FOUND)

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({'msg': 'Patient does not exist'}, status=status.HTTP_404_NOT_FOUND)

    # ✅ Convert and validate appointment date
    if isinstance(appointment_date, str):
        try:
            if len(appointment_date) == 10:
                appointment_date = datetime.strptime(appointment_date, "%Y-%m-%d")
                appointment_date = appointment_date.replace(hour=10, minute=0)
            else:
                appointment_date = datetime.fromisoformat(appointment_date)
            if appointment_date.tzinfo is None:
                appointment_date = make_aware(appointment_date)
        except:
            return Response({"msg": "Invalid date format. Use YYYY-MM-DD or YYYY-MM-DD HH:MM"},
                            status=status.HTTP_400_BAD_REQUEST)

    # ✅ Check appointment is not in the past
    if appointment_date <= now():
        return Response({"msg": "Appointment date must be in the future"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Validate status
    if appointment_status not in ['pending', 'completed', 'cancelled']:
        return Response({"msg": "Invalid status value"}, status=status.HTTP_400_BAD_REQUEST)

    # ✅ Update fields
    appointment.doctor = doctor
    appointment.patient = patient
    appointment.appointment_date = appointment_date
    appointment.status = appointment_status
    appointment.issue_description = issue_description
    appointment.save()

    # ✅ Custom business messages
    if appointment_status == 'completed':
        return Response({'msg': 'Doctor appointment completed successfully'}, status=status.HTTP_200_OK)
    elif appointment_status == 'pending':
        return Response({'msg': 'Doctor appointment is still pending. Please wait.'}, status=status.HTTP_200_OK)
    elif appointment_status == 'cancelled':
        return Response({'msg': 'Doctor appointment has been cancelled.'}, status=status.HTTP_200_OK)

    # ✅ Default success response
    serializer = AppointmentSerializer(appointment)
    return Response({'msg': 'Appointment updated successfully', 'data': serializer.data}, status=status.HTTP_200_OK)


@api_view(['DELETE'])

def Appointment_Delete_Api(request,pk):
    if request.method =='DELETE':
        if pk is not None:
            appointment = Appointment.objects.get(id=pk)
            appointment.delete()
            return Response({'msg':'Appiontments data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'appointment id not correct'},status=status.HTTP_400_BAD_REQUEST)
    

# Hospital MedicalRecords Api 

@api_view(['GET'])

def MedicalRecord_list_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                medical = MedicalRecord.objects.get(id=pk)
            except MedicalRecord.DoesNotExist:
                return Response({'msg':'Patient medical record id not found'},status=status.HTTP_404_NOT_FOUND)
            serialzier = MedicalRecordSerializer(medical)
            return Response(serialzier.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])
def Medical_list_Api(request):
    if request.method == 'GET':
        medicl = MedicalRecord.objects.all()
        serializer = MedicalRecordSerializer(medicl,many=True)
        return Response(serializer.data)
    

@api_view(['POST'])
def MedicalRecord_create_Api(request):
    doctor_id = request.data.get('doctor_id')
    patient_id = request.data.get('patient_id')
    diagnosis = request.data.get('diagnosis')
    prescription = request.data.get('prescription')
    visit_date = request.data.get('visit_date')

    print("Doctor ID received:", doctor_id)
    print("Patient ID received:", patient_id)

    if not diagnosis or not prescription or not visit_date:
        return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        doctor = Doctor.objects.get(id=doctor_id)
    except Doctor.DoesNotExist:
        return Response({"msg": "Doctor does not exist"}, status=status.HTTP_404_NOT_FOUND)

    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"msg": "Patient does not exist"}, status=status.HTTP_404_NOT_FOUND)

    medical = MedicalRecord.objects.create(
        doctor=doctor,
        patient=patient,
        diagnosis=diagnosis,
        prescription=prescription,
        visit_date=visit_date,
    )
    serializer = MedicalRecordSerializer(medical)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['PUT'])

def MedicalRecord_update_Api(request,pk):
    if request.method == 'PUT':
        if pk is not None:
            try:
                medical = MedicalRecord.objects.get(id=pk)
            except MedicalRecord.DoesNotExist:
                return Response({'msg':'Medical Record id not found'},status=status.HTTP_404_NOT_FOUND)
            
            doctor_id = request.data.get('doctor', medical.doctor_id)
            patient_id = request.data.get('patient', medical.patient_id)
            diagnosis = request.data.get('appointment_date', medical.diagnosis)
            prescription = request.data.get('status', medical.prescription)
            visit_date = request.data.get('issue_description', medical.visit_date)


            try:
                doctor = Doctor.objects.get(id=doctor_id)
            except Doctor.DoesNotExist:
                return Response({'msg': 'Doctor does not exist'}, status=status.HTTP_404_NOT_FOUND)

            try:
                patient = Patient.objects.get(id=patient_id)
            except Patient.DoesNotExist:
                return Response({'msg': 'Patient does not exist'}, status=status.HTTP_404_NOT_FOUND)
            
            doctor=doctor,
            patient=patient,
            diagnosis=diagnosis,
            prescription=prescription,
            visit_date=visit_date,
            medical.save()
            serializer = MedicalRecordSerializer(medical)
            return Response({'msg':"Mediacl Record data updated successfully",'data':serializer.data},status=status.HTTP_200_OK)
        return Response({'msg':'Mediacl record id not correct'},status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['DELETE'])

def MedicalRecord_delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            medical = MedicalRecord.objects.get(id=pk)
            medical.delete()
            return Response({'msg':'Medical Record data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'Medical record id not correct'},status=status.HTTP_400_BAD_REQUEST)
    
    
# ***************************** Hospital Patient Medicine Record Api ********************

@api_view(['GET'])

def Medicine_List_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                medicine = Medicine.objects.get(id=pk)
            except Medicine.DoesNotExist:
                return Response({'msg':'Medicine id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = MedicineSerializer(medicine)
            return Response(serializer.data,status=status.HTTP_200_OK)
        

@api_view(['GET'])

def Medicine_Api(request):
    if request.method == 'GET':
        medicine = Medicine.objects.all()
        serializer = MedicineSerializer(medicine,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    



@api_view(['POST'])
def Medicine_Create_Api(request):
    try:
        data = request.data

        # Get data from request
        med_name = data.get('med_name')
        med_type = data.get('med_type')
        stock_quantity = data.get('stock_quantity')
        price = data.get('price')
        expiry_date_str = data.get('expiry_date')

        #  Check for missing fields
        if not all([med_name, med_type, stock_quantity, price, expiry_date_str]):
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        #  Convert stock_quantity and price to correct types
        try:
            stock_quantity = int(stock_quantity)
            price = float(price)
        except ValueError:
            return Response({'msg': 'Stock quantity and price must be numeric'}, status=status.HTTP_400_BAD_REQUEST)

        #  Convert expiry_date (string → date)
        try:
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
        except ValueError:
            return Response({'msg': 'Invalid expiry_date format. Use YYYY-MM-DD'}, status=status.HTTP_400_BAD_REQUEST)

        #  Business logic validation
        if stock_quantity <= 0:
            return Response({'msg': 'Medicine not in stock'}, status=status.HTTP_400_BAD_REQUEST)

        if price <= 0:
            return Response({'msg': 'Price must be positive'}, status=status.HTTP_400_BAD_REQUEST)

        if expiry_date < datetime.now().date():
            return Response({'msg': 'This medicine is expired'}, status=status.HTTP_400_BAD_REQUEST)

        #  Create medicine record
        medicine = Medicine.objects.create(
            med_name=med_name,
            med_type=med_type,
            stock_quantity=stock_quantity,
            price=price,
            expiry_date=expiry_date
        )

        #  Serialize response
        serializer = MedicineSerializer(medicine)
        return Response({
            'msg': 'Medicine record created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'msg': f'Internal Server Error: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['PUT'])
def Medicine_Update_Api(request, pk):
    if request.method == 'PUT':
        try:
            medicine = Medicine.objects.get(id=pk)
        except Medicine.DoesNotExist:
            return Response({'msg': 'Medicine data not found'}, status=status.HTTP_404_NOT_FOUND)

        #  Get updated fields from request data or keep existing
        med_name = request.data.get('med_name', medicine.med_name)
        med_type = request.data.get('med_type', medicine.med_type)
        stock_quantity = request.data.get('stock_quantity', medicine.stock_quantity)
        price = request.data.get('price', medicine.price)
        expiry_date = request.data.get('expiry_date', medicine.expiry_date)

        #  Convert expiry_date if it's a string
        if isinstance(expiry_date, str):
            try:
                expiry_date = datetime.strptime(expiry_date, "%Y-%m-%d").date()
            except ValueError:
                return Response({'msg': 'Invalid expiry_date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        #  Update fields
        medicine.med_name = med_name
        medicine.med_type = med_type
        medicine.stock_quantity = stock_quantity
        medicine.price = price
        medicine.expiry_date = expiry_date
        medicine.save()

        #  Serialize single object (no `many=True`)
        serializer = MedicineSerializer(medicine)
        return Response({'msg': 'Medicine data updated successfully', 'data': serializer.data}, status=status.HTTP_200_OK)
    
@api_view(['DELETE'])

def Medicine_Delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            medicine = Medicine.objects.get(id=pk)
            medicine.delete()
            return Response({'msg':'Medicine data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'Medicine id not correct'},status=status.HTTP_400_BAD_REQUEST)
    

# ***************** Hospital Patient Billing APi ****************

@api_view(['GET'])

def Billing_List_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                billing = Billing.objects.get(id=pk)
            except Billing.DoesNotExist:
                return Response({'msg':'Billing id not found'},status=status.HTTP_400_BAD_REQUEST)
            serializer = BillingSerializer(billing)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])
def Billing_APi_List(request):
    if request.method == 'GET':
        billing = Billing.objects.all()
        serializer = BillingSerializer(billing,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

@api_view(['POST'])

def Billing_Create_Api(request):
    if request.method == 'POST':
        patient_id = request.data.get('patient_id')
        doctor_fee = request.data.get('doctor_fee')
        total_amount = request.data.get('total_amount')
        billing_date = request.data.get('billing_date')
        medicine_cost = request.data.get('medicine_cost')
        room_charges = request.data.get('room_charges')

        #  Validate required fields
        if not patient_id or not doctor_fee or not medicine_cost or not room_charges or not billing_date:
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        #  Check patient existence
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'msg': 'Patient does not exist'}, status=status.HTTP_404_NOT_FOUND)

        #  Convert numeric fields safely
        try:
            doctor_fee = float(doctor_fee)
            medicine_cost = float(medicine_cost)
            room_charges = float(room_charges)
        except ValueError:
            return Response({'msg': 'Numeric fields must contain valid numbers'}, status=status.HTTP_400_BAD_REQUEST)

        #  Business Rules
        if doctor_fee <= 0:
            return Response({'msg': 'Doctor fee must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)
        if medicine_cost <= 0:
            return Response({'msg': 'Medicine cost must be greater than zero'}, status=status.HTTP_400_BAD_REQUEST)
        if room_charges < 0:
            return Response({'msg': 'Room charges cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)

        #  Auto-calculate total amount
        total_amount = doctor_fee + medicine_cost + room_charges

        #  Create record
        billing = Billing.objects.create(
            patient=patient,
            doctor_fee=doctor_fee,
            medicine_cost=medicine_cost,
            room_charges=room_charges,
            total_amount=total_amount,
            billing_date = billing_date,
        )

        serializer = BillingSerializer(billing)
        return Response({
            'msg': 'Billing record created successfully',
            'total_amount': total_amount,
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
    

@api_view(['PUT'])

def Billing_update_Api(request, pk):
    try:
        billing = Billing.objects.get(id=pk)
    except Billing.DoesNotExist:
        return Response({'msg': 'Billing record not found'}, status=status.HTTP_404_NOT_FOUND)

    #  Get updated data
    doctor_fee = request.data.get('doctor_fee', billing.doctor_fee)
    medicine_cost = request.data.get('medicine_cost', billing.medicine_cost)
    room_charges = request.data.get('room_charges', billing.room_charges)

    #  Recalculate total amount if any cost changes
    try:
        total_amount = float(doctor_fee) + float(medicine_cost) + float(room_charges)
    except ValueError:
        return Response({'msg': 'Numeric fields must be valid numbers'}, status=status.HTTP_400_BAD_REQUEST)

    #  Prepare updated data
    data = {
        'patient': billing.patient.id,  # keep same patient
        'doctor_fee': doctor_fee,
        'medicine_cost': medicine_cost,
        'room_charges': room_charges,
        'total_amount': total_amount
    }

    #  Use serializer with partial update enabled
    serializer = BillingSerializer(billing, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({
            'msg': 'Billing data updated successfully',
            'data': serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
@api_view(['DELETE'])

def Billing_Delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            billing = Billing.objects.get(id=pk)
            billing.delete()
            return Response({'msg':'Billing data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'Billing id not correct'},status=status.HTTP_400_BAD_REQUEST)
    

# ************************* Hospital Patient Room APi ********************** 


@api_view(['GET'])
def room_count(request):
    total = Room.objects.count()
    return Response({"total_rooms": total})


@api_view(['GET'])

def Patient_Room_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                room = Room.objects.get(id=pk)
            except Room.DoesNotExist:
                return Response({'msg':'Patient Room id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = RoomSerializer(room)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])
def Patient_Room_List_Api(request):
    if request.method == 'GET':
        room = Room.objects.all()
        serializer = RoomSerializer(room,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

def patientroom_page(request):
    return render(request, "patientroom.html")


    

@api_view(['POST'])
def Patient_Room_Create_Api(request):
    room_name = request.data.get('Room')
    room_number = request.data.get('room_number')
    room_type = request.data.get('room_type')
    room_charges_per_day = request.data.get('room_charges_per_day')

    #  Missing fields
    if not room_name or not room_number or not room_type or not room_charges_per_day:
        return Response({'msg': 'Missing required fields.'}, status=status.HTTP_400_BAD_REQUEST)

    # 2️⃣ Room category validation
    valid_rooms = ["General Ward", "Semi Private", "Private", "ICU"]
    if room_name not in valid_rooms:
        return Response({'msg': f"Invalid Room category. Must be one of {valid_rooms}"},
                        status=status.HTTP_400_BAD_REQUEST)

    #  Type validation
    try:
        room_number = int(room_number)
        room_charges_per_day = float(room_charges_per_day)
    except ValueError:
        return Response({'msg': 'room_number must be integer and charges must be numeric.'},
                        status=status.HTTP_400_BAD_REQUEST)

    #  Positive charge validation
    if room_charges_per_day <= 0:
        return Response({'msg': 'Room charge must be greater than zero.'},
                        status=status.HTTP_400_BAD_REQUEST)

    #  Now this uses the model, not the string
    if Room.objects.filter(room_number=room_number).exists():
        return Response({'msg': f'Room number {room_number} already exists.'},
                        status=status.HTTP_409_CONFLICT)

    #  Business logic rules
    if room_name == "ICU" and room_charges_per_day < 5000:
        return Response({'msg': 'ICU room charges must be at least ₹5000 per day.'},
                        status=status.HTTP_400_BAD_REQUEST)

    if room_name == "General Ward" and room_charges_per_day > 2000:
        return Response({'msg': 'General Ward charges cannot exceed ₹2000 per day.'},
                        status=status.HTTP_400_BAD_REQUEST)

    #  Save to DB
    data = {
        "Room": room_name,
        "room_number": room_number,
        "room_type": room_type,
        "room_charges_per_day": room_charges_per_day
    }

    serializer = RoomSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response({'msg': 'Patient Room created successfully.', 'data': serializer.data},
                        status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])

def Patient_Room_update_Api(request,pk):
    if request.method == 'PUT':
        if pk is not None:
            try:
                room = Room.objects.get(id=pk)
            except Room.DoesNotExist:
                return Response({'msg':'Room id not found '},status=status.HTTP_200_OK)
            serializer = RoomSerializer(room,data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'msg':'Patient room data updated successfully'},status=status.HTTP_200_OK)
            return Response({'msg':'Patient room id not correct'},status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])

def Patient_Room_Delete_Api(request,pk):
    if request.method == 'DELETE':
        room = Room.objects.get(id=pk)
        room.delete()
        return Response({'msg':'Room data deleted successfully'},status=status.HTTP_200_OK)
    return Response({'msg':'Patient room id not correct'},status=status.HTTP_400_BAD_REQUEST)


# ******************************* Hospital Patient Room Admission Api *****************************
    
@api_view(['GET'])

def Patient_Room_Admission_List_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                roomadmission = PatientRoomAdmission.objects.get(id=pk)
            except PatientRoomAdmission.DoesNotExist:
                return Response({'msg':'patient room admission id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = PatientRoomAdmissionSerializer(roomadmission)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])

def Patient_Admission_Room_Api(request):
    if request.method == 'GET':
        roomadmission = PatientRoomAdmission.objects.all()
        serializer = PatientRoomAdmissionSerializer(roomadmission,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)

# Patient Room Admission Data Create Api 

@api_view(['POST'])

def Patient_Room_Admission_Create_Api(request):
    """
    API to admit a patient into a room with business logic validations.
    """

    patient_id = request.data.get('patient_id')
    room_id = request.data.get('room_id')
    admitted_date = request.data.get('admitted_date')
    discharge_date = request.data.get('discharge_date')
    is_active = request.data.get('is_active', True)

    # Validate required fields
    if not patient_id or not room_id or not admitted_date:
        return Response(
            {"msg": "Missing required fields: patient_id, room_id, and admitted_date are mandatory."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate patient existence
    try:
        patient = Patient.objects.get(id=patient_id)
    except Patient.DoesNotExist:
        return Response({"msg": "Patient not found."}, status=status.HTTP_404_NOT_FOUND)

    # Validate room existence
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return Response({"msg": "Room not found."}, status=status.HTTP_404_NOT_FOUND)

    # Parse and validate dates
    try:
        admitted_date = datetime.fromisoformat(admitted_date)
        if discharge_date:
            discharge_date = datetime.fromisoformat(discharge_date)
            if discharge_date < admitted_date:
                return Response(
                    {"msg": "Discharge date cannot be earlier than admission date."},
                    status=status.HTTP_400_BAD_REQUEST
                )
    except ValueError:
        return Response(
            {"msg": "Invalid date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Check if the room is already occupied
    if PatientRoomAdmission.objects.filter(room=room, is_active=True).exists():
        return Response(
            {"msg": f"Room {room.room_number} is currently occupied. Please choose another room."},
            status=status.HTTP_409_CONFLICT
        )

    # Optional: Prevent multiple active admissions for the same patient
    if PatientRoomAdmission.objects.filter(patient=patient, is_active=True).exists():
        return Response(
            {"msg": f"Patient {patient.full_name} already has an active room assignment."},
            status=status.HTTP_409_CONFLICT
        )

    # Create admission record
    admission = PatientRoomAdmission.objects.create(
        patient=patient,
        room=room,
        admitted_date=admitted_date,
        discharge_date=discharge_date,
        is_active=is_active
    )

    serializer = PatientRoomAdmissionSerializer(admission)
    return Response(
        {"msg": "Patient admitted successfully.", "data": serializer.data},
        status=status.HTTP_201_CREATED
    )



@api_view(['PUT'])

def Patient_Admission_Room_update_Api(request, pk):
    if not pk:
        return Response({'msg': 'Patient Admission ID is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Check if the admission record exists
    try:
        admission = PatientRoomAdmission.objects.get(id=pk)
    except PatientRoomAdmission.DoesNotExist:
        return Response(
            {'msg': 'Patient Admission record not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Extract updated data
    patient_id = request.data.get('patient')
    room_id = request.data.get('room')
    admitted_date = request.data.get('admitted_date')
    discharge_date = request.data.get('discharge_date')
    is_active = request.data.get('is_active')

    # Validate patient if provided
    if patient_id:
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'msg': 'Invalid patient ID'}, status=status.HTTP_400_BAD_REQUEST)
        admission.patient = patient

    #  Validate room if provided
    if room_id:
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return Response({'msg': 'Invalid room ID'}, status=status.HTTP_400_BAD_REQUEST)

        # Check if room is already occupied by another active patient
        if PatientRoomAdmission.objects.filter(room=room, is_active=True).exclude(id=pk).exists():
            return Response(
                {'msg': f'Room {room.room_number} is currently occupied by another patient.'},
                status=status.HTTP_409_CONFLICT
            )
        admission.room = room

    # Validate date logic
    if admitted_date:
        try:
            admission.admitted_date = datetime.fromisoformat(admitted_date)
        except ValueError:
            return Response({'msg': 'Invalid admitted_date format. Use ISO (YYYY-MM-DDTHH:MM:SS).'},
                            status=status.HTTP_400_BAD_REQUEST)

    if discharge_date:
        try:
            admission.discharge_date = datetime.fromisoformat(discharge_date)
        except ValueError:
            return Response({'msg': 'Invalid discharge_date format. Use ISO (YYYY-MM-DDTHH:MM:SS).'},
                            status=status.HTTP_400_BAD_REQUEST)

        if admission.discharge_date < admission.admitted_date:
            return Response(
                {'msg': 'Discharge date cannot be earlier than admitted date.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    # Handle active/inactive admission status
    if is_active is not None:
        is_active = bool(is_active)
        admission.is_active = is_active

        # Auto-update room status logic (if model has status field)
        if hasattr(admission.room, 'status'):
            if is_active:
                admission.room.status = 'occupied'
            else:
                admission.room.status = 'available'
            admission.room.save()

    # Save admission record
    admission.save()

    serializer = PatientRoomAdmissionSerializer(admission)
    return Response(
        {
            'msg': 'Patient Admission Room record updated successfully.',
            'data': serializer.data
        },
        status=status.HTTP_200_OK
    )


@api_view(['DELETE'])

def Patient_Admission_Room_Delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            roomadmission = PatientRoomAdmission.objects.get(id=pk)
            roomadmission.delete()
            return Response({'msg':'Patient Room Admisiion data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'Patient room admission id not correct'},status=status.HTTP_400_BAD_REQUEST)
    

# ********************** Hospital Patient Lab Test Record Api ***********************

@api_view(['GET'])

def Patient_LabTest_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                labtest = LabTest.objects.get(id=pk)
            except LabTest.DoesNotExist:
                return Response({'msg':'Patient Labtest record not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = LabTestSerializer(labtest)
            return Response(serializer.data,status=status.HTTP_200_OK)




@api_view(['GET'])

def Patient_LabTest_List_Api(request):
    if request.method == 'GET':
        labtest = LabTest.objects.all()
        serializer = LabTestSerializer(labtest,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

def labtests_page(request):
    return render(request, "labtests.html") 
    

@api_view(['POST'])

def Patient_LabTest_Create_Api(request):

    test_name = request.data.get('test_name')
    test_price = request.data.get('test_price')
    description = request.data.get('description')

    #  Check for required fields
    if not test_name or not test_price or not description:
        return Response(
            {'msg': 'Missing required fields. Please provide test_name, test_price, and description.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate string fields
    try:
        test_name = str(test_name).strip()
        description = str(description).strip()
    except Exception:
        return Response(
            {'msg': 'Test name and description must be valid strings.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate price field
    try:
        test_price = float(test_price)
    except ValueError:
        return Response(
            {'msg': 'Test price must be a valid numeric value.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if test_price <= 0:
        return Response(
            {'msg': 'Test price must be greater than zero.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    #  Check for duplicate test names (case-insensitive)
    if LabTest.objects.filter(test_name__iexact=test_name).exists():
        return Response(
            {'msg': f'A test with the name "{test_name}" already exists.'},
            status=status.HTTP_409_CONFLICT
        )

    #  Save to database
    data = {
        "test_name": test_name,
        "test_price": test_price,
        "description": description
    }

    serializer = LabTestSerializer(data=data)
    if serializer.is_valid():
        serializer.save()
        return Response(
            {
                'msg': 'Lab test created successfully.',
                'data': serializer.data
            },
            status=status.HTTP_201_CREATED
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])

def Patient_Lab_Test_update_Api(request, pk):
    if request.method == 'PUT':
        if pk is not None:
            try:
                labtest = LabTest.objects.get(id=pk)
            except LabTest.DoesNotExist:
                return Response({'msg': 'LabTest record not found'}, status=status.HTTP_404_NOT_FOUND)

            # Fetch data from request
            test_name = request.data.get('test_name')
            test_price = request.data.get('test_price')
            description = request.data.get('description')

            if not test_name and not test_price and not description:
                return Response({'msg': 'No data provided for update'}, status=status.HTTP_400_BAD_REQUEST)
            
            if test_price:
                try:
                    test_price = float(test_price)
                    if test_price <= 0:
                        return Response({'msg': 'Test price must be greater than 0'}, status=status.HTTP_400_BAD_REQUEST)
                except ValueError:
                    return Response({'msg': 'Invalid price value'}, status=status.HTTP_400_BAD_REQUEST)
            
            if test_name and len(test_name.strip()) < 3:
                return Response({'msg': 'Test name must be at least 3 characters long'}, status=status.HTTP_400_BAD_REQUEST)
            
            if test_name:
                labtest.test_name = test_name
            if test_price:
                labtest.test_price = test_price
            if description:
                labtest.description = description

            # Save the updated data in record
            labtest.save()

            return Response({'msg': 'LabTest updated successfully'}, status=status.HTTP_200_OK)

        return Response({'msg': 'Invalid ID'}, status=status.HTTP_400_BAD_REQUEST)
    
    return Response({'msg': 'Invalid request method'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

@api_view(['DELETE'])

def Patient_LabTest_Delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            labtest = LabTest.objects.get(id=pk)
            labtest.delete()
            return Response({'msg':'LabTest Data Deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'Lab Test id not found '},status=status.HTTP_400_BAD_REQUEST)
    

# Hospital patient Lab Test Request Record Api 

@api_view(['GET'])

# LabReuest check only one particular data api

def LabTest_Request_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                labrecord = LabTestRequest.objects.get(id=pk)
            except LabTestRequest.DoesNotExist:
                return Response({'msg':'Lab Test Request record not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = LabTestRequestSerializer(labrecord)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])

# Lab Request show all data in list api 

def Lab_Request_List_Api(request):
    if request.method == 'POST':
        labrequest = LabTestRequest.objects.all()
        serializer = LabTestRequestSerializer(labrequest,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

@api_view(['POST'])

# Lab Request data Created api

def Lab_Test_request_Create_Api(request):
    if request.method == 'POST':
        status_value = request.data.get('status')
        patient = request.data.get('patient')
        doctor = request.data.get('doctor')
        test = request.data.get('test')

        if not status_value or not patient or not doctor or not test:
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        if status_value not in ['requested', 'completed']:
            return Response({'msg': "Invalid status value. Must be 'requested' or 'completed'."},
                            status=status.HTTP_400_BAD_REQUEST)

        if LabTestRequest.objects.filter(patient_id=patient, test_id=test, status='requested').exists():
            return Response({'msg': 'Pending lab test request already exists for this patient and test'},
                            status=status.HTTP_409_CONFLICT)

        new_request = LabTestRequest.objects.create(
            patient_id=patient,
            doctor_id=doctor,
            test_id=test,
            status=status_value
        )

        return Response({
            'msg': 'Lab Test Request created successfully',
            'data': {
                'id': new_request.id,
                'status': new_request.status,
                'patient_id': new_request.patient.id,
                'patient_name': new_request.patient.full_name,
                'doctor_id': new_request.doctor.id,
                'doctor_name': new_request.doctor.full_name,   
                'test_id': new_request.test.id,
                'test_name': new_request.test.test_name,
                'request_date': new_request.request_date
            }
        }, status=status.HTTP_201_CREATED)



@api_view(['PUT'])

# Hospital Patient Lab Test Request Record data update api

def Lab_Test_Request_Update_Api(request,pk):
    if request.method == 'PUT':
        if pk is not None:
            try:
                lab = LabTestRequest.objects.get(id=pk)
            except LabTestRequest.DoesNotExist:
                return Response({'msg':'lab test request id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = LabTestRequestSerializer(lab,data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response({'msg':'Lab Test request data updated successfully'},status=status.HTTP_200_OK)
            return Response({'msg':'Lab Test request record id not found'},status=status.HTTP_400_BAD_REQUEST)
        
@api_view(['DELETE'])

def Lab_Test_Request_Delete_Api(request,pk):
    if request.method == 'DELETE':
        if pk is not None:
            labtest = LabTestRequest.objects.get(id=pk)
            labtest.delete()
            return Response({'msg':'Lab Test request data deleted successfully'},status=status.HTTP_200_OK)
        return Response({'msg':'lab test request data not correct'},status=status.HTTP_400_BAD_REQUEST)
    


# Hospital Patinet Lab Result Api

@api_view(['GET'])

def Patient_Lab_Result_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                labresult = LabResult.objects.get(id=pk)
            except LabResult.DoesNotExist:
                return Response({'msg':'lab result id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = LabResultSerializer(labresult)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
@api_view(['GET'])

def Patient_lab_Result_List_Api(request):
    if request.method == 'GET':
        labres = LabResult.objects.all()
        serialzier = LabResultSerializer(labres,many=True)
        return Response(serialzier.data,status=status.HTTP_200_OK)
    

@api_view(['POST'])
def Patient_Lab_Result_Create_Api(request):
    if request.method == 'POST':

        lab_request_id = request.data.get('lab_request')
        result_report_file = request.FILES.get('result_report_file')
        result_date = request.data.get('result_date')

        # 1. Check Required fields validation
        if not lab_request_id or not result_report_file or not result_date:
            return Response({'msg': 'Missing required fields'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 2.Check  LabRequest exists check
        try:
            lab_req_obj = LabTestRequest.objects.get(id=lab_request_id)
        except LabTestRequest.DoesNotExist:
            return Response({'msg': 'Lab Request ID not found'},
                            status=status.HTTP_404_NOT_FOUND)

        # 3. Check Prevent duplicate LabResult for same LabRequest  
        if LabResult.objects.filter(lab_request=lab_req_obj).exists():
            return Response({'msg': 'Result already created for this Lab Request'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 4. Check Convert result_date to valid datetime
        try:
            parsed_date = datetime.fromisoformat(result_date)
        except:
            return Response({'msg': 'Invalid date format'},
                            status=status.HTTP_400_BAD_REQUEST)

        # 5. Check Create LabResult
        new_result = LabResult.objects.create(
            lab_request=lab_req_obj,
            result_report_file=result_report_file,
            result_date=parsed_date
        )

        serializer = LabResultSerializer(new_result)

        return Response({
            'msg': 'Lab Result created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)  


@api_view(['PUT'])

def Patient_Lab_result_update_Api(request,pk):
    if request.method == 'PUT':
        if pk is not None:
            try:
                labresult = LabResult.objects.get(id=pk)
            except LabResult.DoesNotExist:
                return Response({'msg':'Lab test record not found'},status=status.HTTP_404_NOT_FOUND)
            lab_request = request.data.get('lab_request')
            result_report_file = request.FILES.get('result_report_file')   
            result_date = request.data.get('result_date')

            # Validation
            if not lab_request or not result_date:
                return Response({'msg': 'lab_request and result_date are required'}, status=status.HTTP_400_BAD_REQUEST)

            # Validate lab_request ID
            try:
                lab_request_obj = LabTestRequest.objects.get(id=lab_request)
            except LabTestRequest.DoesNotExist:
                return Response({'msg': 'Invalid lab_request ID'}, status=status.HTTP_404_NOT_FOUND)

            if LabResult.objects.filter(lab_request_id=lab_request).exclude(id=pk).exists():
                return Response({'msg': 'This Lab Request already has a result!'}, status=status.HTTP_409_CONFLICT)

            # Update fields
            labresult.lab_request = lab_request_obj
            labresult.result_date = result_date

            
            if result_report_file:
                labresult.result_report_file = result_report_file

            labresult.save()

            return Response({
                'msg': 'Lab Result updated successfully',
                'data': {
                    'id': labresult.id,
                    'lab_request_id': labresult.lab_request.id,
                    'patient_name': labresult.lab_request.patient.full_name,
                    'test_name': labresult.lab_request.test.test_name,
                    'result_report_file': labresult.result_report_file.url if labresult.result_report_file else None,
                    'result_date': labresult.result_date
                }
            }, status=status.HTTP_200_OK)

@api_view(['DELETE'])

def Patient_Lab_Result_Delete_Api(request,pk):
    if request.method == 'DELETE':
        labresult = LabResult.objects.get(id=pk)
        labresult.delete()
        return Response({'msg':'lab result data deleted successfully'},status=status.HTTP_200_OK)
    return Response({'msg':'lab result id not found'},status=status.HTTP_400_BAD_REQUEST)



# ************************* Hospital Nurse satff  Api *****************************

# Check only one particular nurse staff name another id

@api_view(['GET'])

def Hospital_Nurse_Staff_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                nursestaff = NurseStaff.objects.get(id=pk)
            except NurseStaff.DoesNotExist:
                return Response({'msg':'Nurse staff id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = NurseStaffSerializer(nursestaff)
            return Response(serializer.data,status=status.HTTP_200_OK)
        
# *******************  check show all nurse staff data in list format data ****************** 


def nurselist_page(request):
    return render(request, "nursestaff.html")

@api_view(['GET'])

def Hospital_Nurse_Staff_List_Api(request):
    if request.method == 'GET':
        nursestaff = NurseStaff.objects.all()
        serializer = NurseStaffSerializer(nursestaff,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

# *******************  Create Nurse Staff data Api ***********************


@api_view(['POST'])
def Hospital_Nurse_Staff_Create_Api(request):
    if request.method == 'POST':
        user_id = request.data.get('user')
        full_name = request.data.get('full_name')
        role = request.data.get('role')
        shift_timing = request.data.get('shift_timing')
        assigned_ward = request.data.get('assigned_ward')

        if not user_id or not full_name or not role or not shift_timing or not assigned_ward:
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = H_Users.objects.get(id=user_id)
        except H_Users.DoesNotExist:
            return Response({'msg': 'User ID not found'}, status=status.HTTP_404_NOT_FOUND)

        if NurseStaff.objects.filter(user=user).exists():
            return Response({'msg': 'Nurse profile already exists for this user'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        
        nurse = NurseStaff.objects.create(
            user=user,
            full_name=full_name,
            role=role,
            shift_timing=shift_timing,
            assigned_ward=assigned_ward
        )

       
        serializer = NurseStaffSerializer(nurse)

        return Response({
            'msg': 'Nurse staff created successfully',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
def Hospital_Nurse_Staff_Update_Api(request, pk):
   
    try:
        nurse = NurseStaff.objects.get(id=pk)
    except NurseStaff.DoesNotExist:
        return Response({'msg': 'Nurse staff record not found'}, 
                        status=status.HTTP_404_NOT_FOUND)

    
    user_id = request.data.get('user')
    full_name = request.data.get('full_name')
    role = request.data.get('role')
    shift_timing = request.data.get('shift_timing')
    assigned_ward = request.data.get('assigned_ward')

    
    if user_id:
        try:
            user = H_Users.objects.get(id=user_id)
        except H_Users.DoesNotExist:
            return Response({'msg': 'User ID not found'}, 
                            status=status.HTTP_404_NOT_FOUND)


        if NurseStaff.objects.filter(user=user).exclude(id=pk).exists():
            return Response({'msg': 'Another nurse profile already exists for this user'}, 
                            status=status.HTTP_400_BAD_REQUEST)

        nurse.user = user

    if full_name:
        nurse.full_name = full_name

    if role:
        nurse.role = role

    if shift_timing:
        nurse.shift_timing = shift_timing

    if assigned_ward:
        nurse.assigned_ward = assigned_ward

    nurse.save()

    serializer = NurseStaffSerializer(nurse)

    return Response({
        'msg': 'Nurse staff updated successfully',
        'data': serializer.data
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])

def Hospital_nurse_Staff_Delete_Api(request,pk):
    if request.method == 'DELETE':
        nurse = NurseStaff.objects.get(id=pk)
        nurse.delete()
        return Response({'msg':'Hospital Nurse Staff data deleted successfully'},status=status.HTTP_200_OK)
    return Response({'msg':'Hospital nurse staff data not correct'},status=status.HTTP_400_BAD_REQUEST)


# ******************** Hospital Nurse Dutty Api ********************* 

@api_view(['GET'])

def Hospital_Nurse_Duty_log_Api(request,pk):
    if request.method ==  'GET':
        if pk is not None:
            try:
                nurseduty = NurseDutyLog.objects.get(id=pk)
            except NurseDutyLog.DoesNotExist:
                return Response({'msg':'nurse duty log id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = NurseDutyLogSerializer(nurseduty)
            return Response(serializer.data,status=status.HTTP_200_OK)
        

@api_view(['GET'])

def Hospital_Nurse_Duty_Log_List_Api(request):
    if request.method == 'GET':
        nurseduty = NurseDutyLog.objects.all()
        serializer = NurseDutyLogSerializer(nurseduty,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

# Hospital Nurse Duty Log Data Created 

@api_view(['POST'])
def Hospital_Nurse_Duty_Create_Api(request):
    if request.method == 'POST':
        nurse_id = request.data.get('nurse')
        patient_id = request.data.get('patient')
        task_details = request.data.get('task_details')
        timestamp = request.data.get('timestamp')  

        
        if not nurse_id or not patient_id or not task_details:
            return Response(
                {'msg': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            nurse = NurseStaff.objects.get(id=nurse_id)
        except NurseStaff.DoesNotExist:
            return Response(
                {'msg': 'Invalid nurse ID — nurse not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'msg': 'Invalid patient ID — patient not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        if timestamp:
            if NurseDutyLog.objects.filter(nurse=nurse, patient=patient, timestamp=timestamp).exists():
                return Response(
                    {'msg': 'Duty log already exists for this nurse & patient at this timestamp'},
                    status=status.HTTP_409_CONFLICT
                )
        log = NurseDutyLog.objects.create(
            nurse=nurse,
            patient=patient,
            task_details=task_details,
            timestamp=timestamp if timestamp else timezone.now()
        )
        return Response(
            {
                'msg': 'Nurse duty log created successfully',
                'data': {
                    'id': log.id,
                    'nurse': log.nurse.full_name,
                    'patient': log.patient.full_name,
                    'task_details': log.task_details,
                    'timestamp': log.timestamp
                }
            },
            status=status.HTTP_201_CREATED
        )


# Hospital Nurse Staff Duty Data Updated method

@api_view(['PUT'])
def Hospital_Nurse_Duty_Update_Api(request, pk):
    if request.method == 'PUT':

        try:
            duty_log = NurseDutyLog.objects.get(id=pk)
        except NurseDutyLog.DoesNotExist:
            return Response(
                {'msg': 'Duty log record not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        nurse_id = request.data.get('nurse')
        patient_id = request.data.get('patient')
        task_details = request.data.get('task_details')
        timestamp = request.data.get('timestamp')
        
        if not nurse_id or not patient_id or not task_details:
            return Response(
                {'msg': 'Missing required fields'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            nurse = NurseStaff.objects.get(id=nurse_id)
        except NurseStaff.DoesNotExist:
            return Response(
                {'msg': 'Invalid nurse ID'},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response(
                {'msg': 'Invalid patient ID'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if timestamp:
            if NurseDutyLog.objects.filter(
                    nurse=nurse,
                    patient=patient,
                    timestamp=timestamp
                ).exclude(id=pk).exists():
                return Response(
                    {'msg': 'Another duty log already exists for this time'},
                    status=status.HTTP_409_CONFLICT
                )
        
        if timestamp:
            try:
                parsed_timestamp = datetime.fromisoformat(timestamp)
            except:
                return Response(
                    {'msg': 'Invalid timestamp format'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:
            parsed_timestamp = duty_log.timestamp  

        duty_log.nurse = nurse
        duty_log.patient = patient
        duty_log.task_details = task_details
        duty_log.timestamp = parsed_timestamp
        duty_log.save()

        return Response(
            {
                'msg': 'Duty log updated successfully',
                'data': {
                    'id': duty_log.id,
                    'nurse': duty_log.nurse.full_name,
                    'patient': duty_log.patient.full_name,
                    'task_details': duty_log.task_details,
                    'timestamp': duty_log.timestamp
                }
            },
            status=status.HTTP_200_OK
        )


@api_view(['DELETE'])

def Hospital_Nurse_Duty_Log_Delete_Api(request,pk=None):
    if request.method == 'DELETE':
        nursedutylog = NurseDutyLog.objects.get(id=pk)
        nursedutylog.delete()
        return Response({'msg':'nurse duty log data deleted successfully'},status=status.HTTP_200_OK)
    return Response({'msg':"Nurse staff log data not correct"},status=status.HTTP_400_BAD_REQUEST)


# Hospital Patient Payment Api 

@api_view(['GET'])

def Hospital_Payment_Api(request,pk):
    if request.method == 'GET':
        if pk is not None:
            try:
                payment = Payment.objects.get(id=pk)
            except Payment.DoesNotExist:
                return Response({'msg':'Payment id not found'},status=status.HTTP_404_NOT_FOUND)
            serializer = PaymentSerializer(payment)
            return Response(serializer.data,status=status.HTTP_200_OK)

@api_view(['GET'])

def Hospital_Payment_List_Api(request):
    if request.method == 'GET':
        payment = Payment.objects.all()
        serializer = PaymentSerializer(payment,many=True)
        return Response(serializer.data,status=status.HTTP_200_OK)
    

# Hospital Payment data created method

@api_view(['POST'])
def Hospital_Payment_Create_Api(request):
    if request.method == 'POST':
        patient_id = request.data.get('patient')
        billing_id = request.data.get('billing')
        payment_method = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        amount_paid = request.data.get('amount_paid')

        if not patient_id or not billing_id or not payment_method or not transaction_id or not amount_paid:
            return Response({'msg': 'Missing required fields'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            return Response({'msg': 'Patient not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            billing = Billing.objects.get(id=billing_id)
        except Billing.DoesNotExist:
            return Response({'msg': 'Billing ID not found'}, status=status.HTTP_404_NOT_FOUND)

        try:
            amount_paid = decimal.Decimal(amount_paid)
        except:
            return Response({'msg': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

        valid_methods = ['cash', 'upi', 'card', 'netbanking']
        if payment_method not in valid_methods:
            return Response({'msg': 'Invalid payment method'}, status=status.HTTP_400_BAD_REQUEST)

        if amount_paid > billing.total_amount:
            return Response({'msg': 'Amount cannot exceed total bill amount'}, status=status.HTTP_400_BAD_REQUEST)

        payment_status = 'paid' if amount_paid == billing.total_amount else 'partial'

        payment = Payment.objects.create(
            patient=patient,
            billing=billing,
            payment_method=payment_method,
            transaction_id=transaction_id,
            amount_paid=amount_paid,
            payment_status=payment_status
        )

        return Response({'msg': 'Payment created successfully', 'payment_status': payment_status},
                        status=status.HTTP_201_CREATED)



@api_view(['PUT'])
def Hospital_Payment_Update_Api(request, pk):
    if request.method == 'PUT':

        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({'msg': 'Payment ID not found'}, status=status.HTTP_404_NOT_FOUND)

        payment_method = request.data.get('payment_method')
        transaction_id = request.data.get('transaction_id')
        amount_paid = request.data.get('amount_paid')

        valid_methods = ['cash', 'upi', 'card', 'netbanking']
        if payment_method and payment_method not in valid_methods:
            return Response({'msg': 'Invalid payment method'}, status=status.HTTP_400_BAD_REQUEST)

        if amount_paid:
            try:
                amount_paid = decimal.Decimal(amount_paid)
            except:
                return Response({'msg': 'Invalid amount format'}, status=status.HTTP_400_BAD_REQUEST)

            if amount_paid > payment.billing.total_amount:
                return Response({'msg': 'Amount exceeds billing amount'}, status=status.HTTP_400_BAD_REQUEST)

            payment.amount_paid = amount_paid

            if amount_paid == payment.billing.total_amount:
                payment.payment_status = 'paid'
            elif amount_paid == 0:
                payment.payment_status = 'pending'
            else:
                payment.payment_status = 'partial'

        if payment_method:
            payment.payment_method = payment_method

        if transaction_id:
            payment.transaction_id = transaction_id

        payment.save()

        return Response({'msg': 'Payment updated successfully', 'payment_status': payment.payment_status},
                        status=status.HTTP_200_OK)
    

@api_view(['DELETE'])

def Hospital_Payment_Delete_Api(request,pk):
    if request.method == 'DELETE':
        payment = Payment.objects.get(id=pk)
        payment.delete()
        return Response({'msg':'Payment unique data deleted successfully'},status=status.HTTP_200_OK)
    return Response({'msg':'Payment id not correct'},status=status.HTTP_400_BAD_REQUEST)





@api_view(['POST'])
def Send_OTP_Api(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    otp_code = str(random.randint(100000, 999999))
    OTPVerification.objects.update_or_create(
        email=email,
        defaults={'otp_code': otp_code}
    )
    
    send_otp_email.delay(email, otp_code)
    
    return Response({'msg': 'OTP sent successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def Verify_OTP_Api(request):
    email = request.data.get('email')
    otp_code = request.data.get('otp_code')
    
    if not email or not otp_code:
        return Response({'error': 'Email and OTP are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        otp_record = OTPVerification.objects.get(email=email, otp_code=otp_code)
        
        user, created = User.objects.get_or_create(email=email, defaults={'username': email})
        
        otp_record.delete()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            'msg': 'OTP verified successfully',
            'token': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
        
    except OTPVerification.DoesNotExist:
        return Response({'error': 'Invalid OTP or Email'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def ForgotPassword_Api(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'error': 'User with this email does not exist'}, status=status.HTTP_404_NOT_FOUND)
        
    otp_code = str(random.randint(100000, 999999))
    PasswordResetOTP.objects.update_or_create(
        email=email,
        defaults={'otp_code': otp_code}
    )
    
    send_otp_email.delay(email, otp_code)
    
    return Response({'msg': 'Password reset OTP sent successfully'}, status=status.HTTP_200_OK)

@api_view(['POST'])
def ResetPassword_Api(request):
    email = request.data.get('email')
    otp_code = request.data.get('otp_code')
    new_password = request.data.get('new_password')
    
    if not all([email, otp_code, new_password]):
        return Response({'error': 'Email, OTP, and new password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        otp_record = PasswordResetOTP.objects.get(email=email, otp_code=otp_code)
        user = User.objects.get(email=email)
        
        user.set_password(new_password)
        user.save()
        otp_record.delete()
        
        return Response({'msg': 'Password reset successfully'}, status=status.HTTP_200_OK)
        
    except (PasswordResetOTP.DoesNotExist, User.DoesNotExist):
        return Response({'error': 'Invalid OTP or Email'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])

def ChangePassword_Api(request):
    email = request.data.get('email')
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not all([email, old_password, new_password]):
        return Response({'error': 'Email, old_password, and new_password are required'}, status=status.HTTP_400_BAD_REQUEST)
        
    try:
        user = User.objects.get(email=email)
        if not user.check_password(old_password):
            return Response({'error': 'Incorrect old password'}, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        
        return Response({'msg': 'Password changed successfully'}, status=status.HTTP_200_OK)
        
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)