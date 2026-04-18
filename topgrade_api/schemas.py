from ninja import Schema

class LoginSchema(Schema):
    email: str
    password: str

class SignupSchema(Schema):
    fullname: str
    email: str
    phone_number: str
    password: str
    confirm_password: str

class RequestOtpSchema(Schema):
    email: str

class VerifyOtpSchema(Schema):
    email: str
    otp: str

class ResetPasswordSchema(Schema):
    email: str
    new_password: str
    confirm_password: str

class PhoneSigninSchema(Schema):
    phoneNumber: str  # Phone number with country code
    firebaseToken: str  # Firebase ID token from Flutter

class CompleteProfileSchema(Schema):
    email: str
    fullname: str

class RefreshTokenSchema(Schema):
    refresh_token: str

class AreaOfInterestSchema(Schema):
    area_of_intrest: str

class PurchaseSchema(Schema):
    program_id: int
    payment_method: str = 'card'  # optional, defaults to 'card'
 
class BookmarkSchema(Schema):
    program_id: int

class UpdateProgressSchema(Schema):
    topic_id: int
    purchase_id: int  # Specific purchase to ensure correct program/topic mapping
    watch_time_seconds: int

class UpdateProfileSchema(Schema):
    fullname: str = None
    phone_number: str = None
    email: str = None

# Notification Schemas
class RegisterFCMTokenSchema(Schema):
    token: str
    device_type: str = 'android'  # android, ios, web
    device_id: str = None

class MarkNotificationReadSchema(Schema):
    notification_id: int