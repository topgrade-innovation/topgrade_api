from ninja import NinjaAPI
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from topgrade_api.schemas import LoginSchema, SignupSchema, RequestOtpSchema, VerifyOtpSchema, ResetPasswordSchema, RequestPhoneOtpSchema, VerifyPhoneOtpSchema, RefreshTokenSchema, CompleteProfileSchema
from topgrade_api.models import CustomUser, OTPVerification, PhoneOTPVerification
from topgrade_api.utils.sms_helper import send_otp_sms
from topgrade_api.views.common import AuthBearer
from django.utils import timezone
from dashboard.tasks import send_otp_email_task, generate_otp
import time

# Initialize Django Ninja API for authentication
auth_api = NinjaAPI(version="1.0.0", title="Authentication API", urls_namespace="auth")

@auth_api.post("/signin")
def signin(request, credentials: LoginSchema):
    """
    Simple signin API that returns access_token and refresh_token with user data
    """
    user = authenticate(username=credentials.email, password=credentials.password)
    
    if user is not None:
        refresh = RefreshToken.for_user(user)
        return {
            "success": True,
            "message": "Signin successful",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "fullname": user.fullname if user.fullname else "",
                "email": user.email,
                "phone_number": user.phone_number if user.phone_number else "",
            },
            "has_area_of_intrest": bool(user.area_of_intrest and user.area_of_intrest.strip())
        }
    else:
        return JsonResponse({"message": "Invalid credentials"}, status=401)

@auth_api.post("/signup")
def signup(request, user_data: SignupSchema):
    """
    User registration API with user data in response
    """
    # Check if passwords match
    if user_data.password != user_data.confirm_password:
        return JsonResponse({"message": "Passwords do not match"}, status=400)
    
    # Add +91 prefix to phone number if not already present
    phone_number = user_data.phone_number
    if phone_number and not phone_number.startswith('+'):
        phone_number = f"+91{phone_number}"
    
    # Check if user already exists with this email
    if CustomUser.objects.filter(email=user_data.email).exists():
        return JsonResponse({"message": "User with this email already exists"}, status=400)
    
    # Check if phone number is already registered
    if phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
        return JsonResponse({"message": "User with this phone number already exists"}, status=400)
    
    try:
        # Create new user
        user = CustomUser.objects.create_user(
            email=user_data.email,
            password=user_data.password,
            fullname=user_data.fullname,
            phone_number=phone_number
        )
        
        # Generate tokens for immediate login
        refresh = RefreshToken.for_user(user)
        
        return {
            "success": True,
            "message": "User created successfully",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "fullname": user.fullname if user.fullname else "",
                "email": user.email,
                "phone_number": user.phone_number if user.phone_number else "",
            },
            "has_area_of_intrest": bool(user.area_of_intrest and user.area_of_intrest.strip())
        }
    except Exception as e:
        return JsonResponse({"message": "Error creating user"}, status=500)

@auth_api.post("/request-otp")
def request_otp(request, otp_data: RequestOtpSchema):
    """
    Request OTP for password reset - sends OTP via email
    """
    try:
        # Check if user exists
        user = CustomUser.objects.get(email=otp_data.email)
        
        # Generate 6-digit OTP
        otp_code = generate_otp()
        
        # Create or update OTP verification record
        otp_verification, created = OTPVerification.objects.get_or_create(
            email=otp_data.email,
            defaults={
                'otp_code': otp_code,
                'is_verified': False,
                'expires_at': timezone.now() + timezone.timedelta(minutes=10)
            }
        )
        
        # Reset verification status for new OTP request
        if not created:
            otp_verification.otp_code = otp_code
            otp_verification.is_verified = False
            otp_verification.verified_at = None
            otp_verification.expires_at = timezone.now() + timezone.timedelta(minutes=10)
            otp_verification.save()
        
        # Get user's full name
        full_name = user.fullname if user.fullname else user.email.split('@')[0]
        
        # Send OTP email asynchronously using Celery
        send_otp_email_task.delay(otp_data.email, otp_code, 'password_reset', full_name)
        
        return {
            "success": True,
            "message": "OTP sent to your email. Please check your inbox.",
        }
        
    except CustomUser.DoesNotExist:
        return JsonResponse({"message": "User with this email does not exist"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"Error sending OTP: {str(e)}"}, status=500)

@auth_api.post("/verify-otp")
def verify_otp(request, verify_data: VerifyOtpSchema):
    """
    Verify OTP for password reset - verifies the OTP sent via email
    """
    try:
        # Check if user exists
        user = CustomUser.objects.get(email=verify_data.email)
        
        # Check if OTP verification record exists
        try:
            otp_verification = OTPVerification.objects.get(email=verify_data.email)
        except OTPVerification.DoesNotExist:
            return JsonResponse({"message": "No OTP request found. Please request OTP first."}, status=400)
        
        # Check if OTP verification has expired
        if otp_verification.is_expired():
            return JsonResponse({"message": "OTP has expired. Please request a new OTP."}, status=400)
        
        # Check if OTP is correct
        if verify_data.otp != otp_verification.otp_code:
            return JsonResponse({"message": "Invalid OTP. Please check your email and try again."}, status=400)
        
        # Mark OTP as verified
        otp_verification.is_verified = True
        otp_verification.verified_at = timezone.now()
        otp_verification.save()
        
        return {
            "success": True,
            "message": "OTP verified successfully. You can now reset your password.",
        }
        
    except CustomUser.DoesNotExist:
        return JsonResponse({"message": "User with this email does not exist"}, status=404)
    except Exception as e:
        return JsonResponse({"message": f"Error verifying OTP: {str(e)}"}, status=500)

@auth_api.post("/reset-password")
def reset_password(request, reset_data: ResetPasswordSchema):
    """
    Reset password API - allows users to reset their password using email, password, and confirm password
    """
    # Check if passwords match
    if reset_data.new_password != reset_data.confirm_password:
        return JsonResponse({"message": "Passwords do not match"}, status=400)
    
    try:
        # Check if user exists
        user = CustomUser.objects.get(email=reset_data.email)
        
        # Check if OTP was verified
        try:
            otp_verification = OTPVerification.objects.get(email=reset_data.email)
        except OTPVerification.DoesNotExist:
            return JsonResponse({"message": "OTP verification required. Please request and verify OTP first."}, status=400)
        
        # Check if OTP verification is still valid and verified
        if not otp_verification.is_verified:
            return JsonResponse({"message": "OTP not verified. Please verify OTP before resetting password."}, status=400)
        
        if otp_verification.is_expired():
            return JsonResponse({"message": "OTP verification has expired. Please request a new OTP."}, status=400)
        
        # Update the password
        user.set_password(reset_data.new_password)
        user.save()
        
        # Clean up the OTP verification record after successful password reset
        otp_verification.delete()
        
        return {
            "success": True,
            "message": "Password reset successfully"
        }
        
    except CustomUser.DoesNotExist:
        return JsonResponse({"message": "User with this email does not exist"}, status=404)
    except Exception as e:
        return JsonResponse({"message": "Error resetting password"}, status=500)

def _normalize_phone(phone_number):
    """Normalize a phone number to the +91XXXXXXXXXX format used in the DB."""
    phone_number = phone_number.strip()
    if not phone_number.startswith('+'):
        phone_number = f"+91{phone_number}"
    return phone_number

@auth_api.post("/request-phone-otp")
def request_phone_otp(request, otp_data: RequestPhoneOtpSchema):
    """
    Request OTP for phone sign-in - generates an OTP and delivers it via the
    apitxt.com SMS gateway.
    """
    try:
        phone_number = _normalize_phone(otp_data.phone_number)

        # Generate 6-digit OTP
        otp_code = generate_otp()

        # Create or update the OTP verification record for this phone number
        PhoneOTPVerification.objects.update_or_create(
            phone_number=phone_number,
            defaults={
                'otp_code': otp_code,
                'is_verified': False,
                'verified_at': None,
                'expires_at': timezone.now() + timezone.timedelta(minutes=10),
            }
        )

        # Send the OTP synchronously via SMS gateway
        success, message = send_otp_sms(phone_number, otp_code)
        if not success:
            return JsonResponse({"message": message}, status=500)

        return {
            "success": True,
            "message": "OTP sent to your phone. Please check your messages.",
        }

    except Exception as e:
        return JsonResponse({"message": f"Error sending OTP: {str(e)}"}, status=500)

@auth_api.post("/verify-phone-otp")
def verify_phone_otp(request, verify_data: VerifyPhoneOtpSchema):
    """
    Verify the phone OTP and sign the user in. Finds or creates a user by phone
    number and returns JWT tokens on success.
    """
    phone_number = _normalize_phone(verify_data.phone_number)

    # Check if an OTP request exists for this phone number
    try:
        otp_verification = PhoneOTPVerification.objects.get(phone_number=phone_number)
    except PhoneOTPVerification.DoesNotExist:
        return JsonResponse({"message": "No OTP request found. Please request OTP first."}, status=400)

    # Check expiry
    if otp_verification.is_expired():
        return JsonResponse({"message": "OTP has expired. Please request a new OTP."}, status=400)

    # Check OTP value
    if verify_data.otp != otp_verification.otp_code:
        return JsonResponse({"message": "Invalid OTP. Please try again."}, status=400)

    # Find or create the user by phone number
    try:
        user = CustomUser.objects.get(phone_number=phone_number)
    except CustomUser.DoesNotExist:
        try:
            # Generate temporary email for new user
            temp_email = f"{phone_number.replace('+', '')}@temp.phone.com"
            # Use phone number without prefix as password
            password_for_user = phone_number.replace('+91', '') if phone_number.startswith('+91') else phone_number

            user = CustomUser.objects.create_user(
                email=temp_email,  # Temporary email
                phone_number=phone_number,
                fullname="",  # Empty, will be filled later
                password=password_for_user
            )
        except Exception as e:
            return JsonResponse({"message": f"Error creating user: {str(e)}"}, status=500)

    try:
        # Mark OTP verified, then clean it up after a successful sign-in
        otp_verification.delete()

        # Generate JWT tokens for login
        refresh = RefreshToken.for_user(user)

        return {
            "success": True,
            "message": "Signin successful",
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user": {
                "fullname": user.fullname if user.fullname else "",
                "email": user.email,
                "phone_number": user.phone_number if user.phone_number else "",
            },
            "has_area_of_intrest": bool(user.area_of_intrest and user.area_of_intrest.strip())
        }

    except Exception as e:
        return JsonResponse({"message": f"Error during phone signin: {str(e)}"}, status=500)

@auth_api.get("/profile-status", auth=AuthBearer())
def profile_status(request):
    """
    Check if user has completed their profile (email, name, and area of interest)
    Requires authentication: Bearer token in Authorization header
    """
    user = request.auth
    
    # Check if email is temporary (not real)
    is_temp_email = user.email.endswith('@temp.phone.com')
    has_email = not is_temp_email and bool(user.email)
    has_name = bool(user.fullname and user.fullname.strip())
    has_area_of_intrest = bool(user.area_of_intrest and user.area_of_intrest.strip())
    
    response_data = {
        "hasEmail": has_email,
        "hasName": has_name,
        "hasAreaOfInterest": has_area_of_intrest,
        "isProfileComplete": has_email and has_name  # Email + Name are mandatory
    }
    
    # If profile is complete, return user data
    if has_email and has_name:
        response_data["user"] = {
            "email": user.email,
            "fullname": user.fullname,
            "phone_number": user.phone_number if user.phone_number else "",
            "area_of_intrest": user.area_of_intrest if user.area_of_intrest else ""
        }
    
    return response_data

@auth_api.post("/profile-update", auth=AuthBearer())
def profile_update(request, profile_data: CompleteProfileSchema):
    """
    Update user profile with email and fullname
    Requires authentication: Bearer token in Authorization header
    """
    user = request.auth
    email = profile_data.email.strip()
    fullname = profile_data.fullname.strip()
    
    # Validate email and fullname are provided
    if not email or not fullname:
        return JsonResponse({"message": "Email and full name are required"}, status=400)
    
    # Check if email already exists (excluding current user and temp emails)
    if CustomUser.objects.filter(email=email).exclude(id=user.id).exclude(email__endswith='@temp.phone.com').exists():
        return JsonResponse({"message": "This email is already registered"}, status=400)
    
    try:
        # Update user profile
        user.email = email
        user.username = email
        user.fullname = fullname
        user.save()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "user": {
                "email": user.email,
                "fullname": user.fullname,
                "phone_number": user.phone_number if user.phone_number else "",
                "area_of_intrest": user.area_of_intrest if user.area_of_intrest else ""
            },
            "hasAreaOfInterest": bool(user.area_of_intrest and user.area_of_intrest.strip())
        }
    except Exception as e:
        return JsonResponse({"message": f"Error updating profile: {str(e)}"}, status=500)

@auth_api.post("/refresh")
def refresh_token(request, token_data: RefreshTokenSchema):
    """
    Refresh access token using refresh token
    """
    try:
        # Create RefreshToken object from the provided refresh token
        refresh = RefreshToken(token_data.refresh_token)
        
        # Generate new access token
        new_access_token = str(refresh.access_token)
        
        return {
            "success": True,
            "message": "Token refreshed successfully",
            "access_token": new_access_token
        }
        
    except Exception as e:
        return JsonResponse({"message": "Invalid or expired refresh token"}, status=401)