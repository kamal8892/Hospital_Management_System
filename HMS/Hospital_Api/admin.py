from django.contrib import admin
from .models import *

admin.site.register(H_Users)
admin.site.register(Doctor)
admin.site.register(Patient)
admin.site.register(Appointment)
admin.site.register(MedicalRecord)
admin.site.register(Medicine)
admin.site.register(Billing)
admin.site.register(Room)
admin.site.register(PatientRoomAdmission)
admin.site.register(LabTest)
admin.site.register(LabTestRequest)
admin.site.register(LabResult)
admin.site.register(NurseStaff)
admin.site.register(NurseDutyLog)
admin.site.register(Payment)
