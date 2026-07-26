from rest_framework import serializers
from . models import H_Users,Doctor,Patient,Appointment,MedicalRecord,Medicine,Billing,Room,PatientRoomAdmission,LabTest,LabTestRequest,LabResult,NurseStaff,NurseDutyLog,Payment

class H_UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = H_Users
        fields = ['First_name','Last_name','city','phone','email','password']


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = '__all__'

class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = '__all__'

class AppointmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Appointment
        fields = '__all__'


class MedicalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalRecord
        fields = '__all__'

class MedicineSerializer(serializers.ModelSerializer):
    class Meta:
        model = Medicine
        fields = '__all__'


class BillingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Billing
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'



class PatientRoomAdmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientRoomAdmission
        fields = '__all__'


class LabTestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTest
        fields = '__all__'


class LabTestRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestRequest
        fields = '__all__'


class LabResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabResult
        fields = '__all__'


class NurseStaffSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseStaff
        fields = '__all__'

    
class NurseDutyLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NurseDutyLog
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


