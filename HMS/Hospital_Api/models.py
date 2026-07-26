from django.db import models


# Hospital User Details table
class H_Users(models.Model):
    First_name = models.CharField(max_length=100)
    Last_name = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    age = models.IntegerField(null=True, blank=True)
    phone = models.CharField(max_length=15)
    email = models.CharField(max_length=100,default='example@gmail.com')
    gender = models.CharField(max_length=10)
    password = models.CharField(max_length=255,default=True)



    def __str__(self):
        return self.First_name
    

# Hospital Doctor Details Table

class Doctor(models.Model):
    user = models.OneToOneField(H_Users, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    experience_years = models.IntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    photo = models.ImageField(upload_to="doctors/", blank=True, null=True)
    available_from = models.TimeField()
    available_to = models.TimeField()

    def __str__(self):
        return self.full_name
    

# Hospital Patient Record Table

class Patient(models.Model):
    user = models.OneToOneField(H_Users, on_delete=models.SET_NULL, null=True, blank=True)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=10)
    blood_group = models.CharField(max_length=10)
    address = models.TextField()
    emergency_contact = models.CharField(max_length=15)
    registration_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.full_name
    


# Hospital Patient Appointment Records Table

class Appointment(models.Model):
    STATUS_CHOICES = (
    ('pending', 'Pending'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
    )


    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    appointment_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    issue_description = models.TextField()


    def __str__(self):
        return f"{self.patient.full_name} - {self.doctor.full_name}"
    

# Hospital Patients Medical Records Table

    
class MedicalRecord(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    diagnosis = models.TextField()
    prescription = models.TextField()
    visit_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Record of {self.patient.full_name}"
    

# Hospital Patient Medicine Records table.

class Medicine(models.Model):
    med_name = models.CharField(max_length=100)
    med_type = models.CharField(max_length=50)
    stock_quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()


    def __str__(self):
        return self.med_name
    

# Hospital Patients Billing Records table.

class Billing(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor_fee = models.DecimalField(max_digits=10, decimal_places=2)
    medicine_cost = models.DecimalField(max_digits=10, decimal_places=2)
    room_charges = models.DecimalField(max_digits=10, decimal_places=2)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    billing_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Bill for {self.patient.full_name}"
    


# Hospital Patients Room Records Table.

class Room(models.Model):
    ROOM_TYPE = (
    ('general', 'General Ward'),
    ('semi_private', 'Semi Private'),
    ('private', 'Private'),
    ('icu', 'ICU'),
    )


    room_number = models.CharField(max_length=10, unique=True)
    room_type = models.CharField(max_length=30, choices=ROOM_TYPE)
    room_charges_per_day = models.DecimalField(max_digits=10, decimal_places=2)
    # status = models.CharField(max_length=20, default='available')


    def __str__(self):
        return self.room_number
    

# Hospital Patients Room Admission Records Table.

class PatientRoomAdmission(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE)
    admitted_date = models.DateTimeField(auto_now_add=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)


    def __str__(self):
        return f"{self.patient.full_name} in room {self.room.room_number}"
    


# Hospital Patients Lab Test Type Records Table.

class LabTest(models.Model):
    test_name = models.CharField(max_length=100)
    test_price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)


    def __str__(self):
        return self.test_name
    

# Hospital Lab Test Request Records table.

class LabTestRequest(models.Model):
    STATUS_CHOICES = (
    ('requested', 'Requested'),
    ('completed', 'Completed'),
    )


    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE)
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='requested')


    def __str__(self):
        return f"{self.test.test_name} for {self.patient.full_name}"
    

# Hospital Lab Test Result Records Table.

class LabResult(models.Model):
    lab_request = models.OneToOneField(LabTestRequest, on_delete=models.CASCADE)
    result_report_file = models.FileField(upload_to='lab_reports/')
    result_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Result of {self.lab_request.patient.full_name}"
    

# Hospital Nurse Staff  Records table.

class NurseStaff(models.Model):
    user = models.OneToOneField(H_Users, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    role = models.CharField(max_length=50)
    shift_timing = models.CharField(max_length=50)
    assigned_ward = models.CharField(max_length=50)


    def __str__(self):
        return self.full_name
    

# Hospital Nurse Duty Records Table.

class NurseDutyLog(models.Model):
    nurse = models.ForeignKey(NurseStaff, on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    task_details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Duty log of {self.nurse.full_name}"
    


# Hospital Patients Paymets Records Table.

class Payment(models.Model):
    PAYMENT_METHODS = (
    ('cash','CASH'),
    ('upi', 'UPI'),
    ('card', 'Card'),
    ('netbanking', 'Net Banking'),
    )


    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    transaction_id = models.CharField(max_length=100)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=20, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Payment for {self.patient.full_name}"
    
class OTPVerification(models.Model):
    email = models.EmailField(unique=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"OTP for {self.email}"
class PasswordResetOTP(models.Model):
    email = models.EmailField(unique=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Password Reset OTP for {self.email}"
