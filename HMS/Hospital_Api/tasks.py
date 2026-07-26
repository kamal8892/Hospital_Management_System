from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_otp_email(email, otp_code):
    subject = 'Your Healing Haven Authentication OTP'
    message = f'Hello,\n\nYour One-Time Password (OTP) for authentication is: {otp_code}\n\nThis code will expire shortly.\n\nThank you,\nHealing Haven Hospital'
    email_from = settings.EMAIL_HOST_USER
    recipient_list = [email]
    
    send_mail(subject, message, email_from, recipient_list)
    return f"OTP {otp_code} sent to {email}"
