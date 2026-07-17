"""
Profile view for mobile app - returns student-related data
"""
import re
from django.http import JsonResponse
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone
from topgrade_api.models import (
    CustomUser, UserPurchase, UserBookmark, UserCourseProgress, UserTopicProgress,
    OTPVerification, PhoneOTPVerification
)
from topgrade_api.schemas import (
    UpdateProfileSchema, RequestProfileChangeOtpSchema, VerifyProfileChangeOtpSchema
)
from topgrade_api.utils.sms_helper import send_otp_sms
from dashboard.tasks import generate_otp, send_otp_email_task
from .common import api, AuthBearer

# Temp email domains assigned to phone-OTP accounts before a real email is added
TEMP_EMAIL_DOMAINS = ('@temp.phone.com', '@tempuser.com')

# How long a verified OTP stays usable for the final profile update
VERIFIED_OTP_VALIDITY_MINUTES = 30


def _is_phone_otp_user(user):
    """Check if user registered via phone OTP (still has a temp email)."""
    return bool(user.email) and user.email.endswith(TEMP_EMAIL_DOMAINS)


def _normalize_phone(phone_number):
    """Normalize a phone number to the +91XXXXXXXXXX format used in the DB."""
    phone_number = phone_number.strip()
    if not phone_number.startswith('+'):
        phone_number = f"+91{phone_number}"
    return phone_number


def _mask_phone(phone_number):
    return f"{phone_number[:3]}******{phone_number[-3:]}" if len(phone_number) > 6 else phone_number


def _mask_email(email):
    local, _, domain = email.partition('@')
    masked_local = local[:2] + '***' if len(local) > 2 else '***'
    return f"{masked_local}@{domain}"


@api.get("/profile", auth=AuthBearer())
def get_user_profile(request):
    """
    Get comprehensive user profile data for mobile app
    Returns user info, purchase stats, bookmarks, and learning progress
    """
    user = request.auth

    try:
        is_phone_otp_user = _is_phone_otp_user(user)

        # Basic user information
        profile_data = {
            "user_info": {
                "id": user.id,
                "email": "" if is_phone_otp_user else user.email,
                "fullname": user.fullname or "",
                "phone_number": user.phone_number or "",
                "can_update_phone": True,  # Any user can change phone via OTP verification
                "can_update_email": True,  # Any user can change email via OTP verification
                "registration_type": "phone_otp" if is_phone_otp_user else "email"
            }
        }

        # Quick stats calculation
        total_purchases = UserPurchase.objects.filter(user=user).count()
        total_bookmarks = UserBookmark.objects.filter(user=user).count()

        # Learning progress
        course_progress = UserCourseProgress.objects.filter(user=user)
        total_courses = course_progress.count()
        completed_courses = course_progress.filter(is_completed=True).count()

        # Recent activity count (last 7 days)
        seven_days_ago = timezone.now() - timezone.timedelta(days=7)
        recent_activity_count = UserTopicProgress.objects.filter(
            user=user,
            last_watched_at__gte=seven_days_ago
        ).count()

        stats = {
            "total_purchases": total_purchases,
            "total_bookmarks": total_bookmarks,
            "total_courses": total_courses,
            "completed_courses": completed_courses,
            "completion_rate": round((completed_courses / total_courses * 100) if total_courses > 0 else 0, 1),
            "recent_activity_count": recent_activity_count
        }

        # Combine all data
        profile_data.update({
            "learning_stats": stats,
        })

        return {
            "success": True,
            "data": profile_data
        }

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error retrieving profile data: {str(e)}"
        }, status=500)


def _validate_change_value(user, field, new_value):
    """
    Validate and normalize the requested new phone/email.
    Returns (normalized_value, error_response). error_response is None when valid.
    """
    if field == "phone":
        new_value = _normalize_phone(new_value)
        if not re.match(r'^\+\d{10,15}$', new_value):
            return None, JsonResponse({
                "success": False,
                "message": "Invalid phone number format"
            }, status=400)
        if user.phone_number == new_value:
            return None, JsonResponse({
                "success": False,
                "message": "This is already your current phone number"
            }, status=400)
        if CustomUser.objects.filter(phone_number=new_value).exclude(id=user.id).exists():
            return None, JsonResponse({
                "success": False,
                "message": "This phone number is already registered with another account"
            }, status=400)
    else:  # email
        new_value = new_value.strip().lower()
        try:
            validate_email(new_value)
        except ValidationError:
            return None, JsonResponse({
                "success": False,
                "message": "Invalid email address"
            }, status=400)
        if new_value.endswith(TEMP_EMAIL_DOMAINS):
            return None, JsonResponse({
                "success": False,
                "message": "Invalid email address"
            }, status=400)
        if user.email and user.email.lower() == new_value:
            return None, JsonResponse({
                "success": False,
                "message": "This is already your current email"
            }, status=400)
        if CustomUser.objects.filter(email__iexact=new_value).exclude(id=user.id).exists():
            return None, JsonResponse({
                "success": False,
                "message": "This email is already registered with another account"
            }, status=400)

    return new_value, None


@api.post("/profile/request-change-otp", auth=AuthBearer())
def request_profile_change_otp(request, data: RequestProfileChangeOtpSchema):
    """
    Send an OTP to a NEW phone number (SMS) or NEW email to verify ownership
    before the user can update it on their profile.
    """
    user = request.auth

    if data.field not in ("phone", "email"):
        return JsonResponse({
            "success": False,
            "message": "Invalid field. Must be 'phone' or 'email'."
        }, status=400)

    try:
        new_value, error = _validate_change_value(user, data.field, data.new_value)
        if error:
            return error

        otp_code = generate_otp()
        now = timezone.now()

        if data.field == "phone":
            existing = PhoneOTPVerification.objects.filter(phone_number=new_value).first()
            if existing and existing.created_at > now - timezone.timedelta(seconds=60):
                return JsonResponse({
                    "success": False,
                    "message": "Please wait a minute before requesting another OTP"
                }, status=429)

            PhoneOTPVerification.objects.update_or_create(
                phone_number=new_value,
                defaults={
                    'otp_code': otp_code,
                    'is_verified': False,
                    'verified_at': None,
                    'expires_at': now + timezone.timedelta(minutes=10),
                    'created_at': now,
                }
            )
            success, message = send_otp_sms(new_value, otp_code)
            if not success:
                return JsonResponse({"success": False, "message": message}, status=500)
            masked = _mask_phone(new_value)
        else:
            existing = OTPVerification.objects.filter(email=new_value).first()
            if existing and existing.created_at > now - timezone.timedelta(seconds=60):
                return JsonResponse({
                    "success": False,
                    "message": "Please wait a minute before requesting another OTP"
                }, status=429)

            OTPVerification.objects.update_or_create(
                email=new_value,
                defaults={
                    'otp_code': otp_code,
                    'is_verified': False,
                    'verified_at': None,
                    'expires_at': now + timezone.timedelta(minutes=10),
                    'created_at': now,
                }
            )
            send_otp_email_task.delay(new_value, otp_code, otp_type='signup', full_name=user.fullname or 'User')
            masked = _mask_email(new_value)

        return {
            "success": True,
            "message": f"OTP sent to {masked}",
            "expires_in": 600
        }

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error sending OTP: {str(e)}"
        }, status=500)


@api.post("/profile/verify-change-otp", auth=AuthBearer())
def verify_profile_change_otp(request, data: VerifyProfileChangeOtpSchema):
    """
    Verify the OTP sent to the new phone/email. Marks the value as verified;
    the change itself is applied by PUT /profile/update.
    """
    if data.field not in ("phone", "email"):
        return JsonResponse({
            "success": False,
            "message": "Invalid field. Must be 'phone' or 'email'."
        }, status=400)

    try:
        if data.field == "phone":
            new_value = _normalize_phone(data.new_value)
            otp_record = PhoneOTPVerification.objects.filter(phone_number=new_value).first()
        else:
            new_value = data.new_value.strip().lower()
            otp_record = OTPVerification.objects.filter(email=new_value).first()

        if not otp_record:
            return JsonResponse({
                "success": False,
                "message": "No OTP request found. Please request OTP first."
            }, status=400)

        if otp_record.is_expired():
            otp_record.delete()
            return JsonResponse({
                "success": False,
                "message": "OTP has expired. Please request a new OTP."
            }, status=400)

        if data.otp != otp_record.otp_code:
            return JsonResponse({
                "success": False,
                "message": "Invalid OTP. Please try again."
            }, status=400)

        otp_record.is_verified = True
        otp_record.verified_at = timezone.now()
        otp_record.save()

        return {
            "success": True,
            "message": "Verified successfully",
            "field": data.field,
            "new_value": new_value
        }

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error verifying OTP: {str(e)}"
        }, status=500)


def _get_verified_otp_record(field, new_value):
    """Return a verified, still-valid OTP record for the new value, or None."""
    if field == "phone":
        record = PhoneOTPVerification.objects.filter(phone_number=new_value, is_verified=True).first()
    else:
        record = OTPVerification.objects.filter(email=new_value, is_verified=True).first()

    if not record or not record.verified_at:
        return None
    if record.verified_at < timezone.now() - timezone.timedelta(minutes=VERIFIED_OTP_VALIDITY_MINUTES):
        record.delete()
        return None
    return record


@api.put("/profile/update", auth=AuthBearer())
def update_user_profile(request, data: UpdateProfileSchema):
    """
    Update user profile information.
    Fullname updates directly; phone/email changes require a prior OTP
    verification via /profile/request-change-otp + /profile/verify-change-otp.
    """
    user = request.auth

    try:
        if data.fullname:
            user.fullname = data.fullname

        if data.email:
            new_email = data.email.strip().lower()
            if not (user.email and user.email.lower() == new_email):
                # Race-safe uniqueness re-check at apply time
                if CustomUser.objects.filter(email__iexact=new_email).exclude(id=user.id).exists():
                    return JsonResponse({
                        "success": False,
                        "message": "This email is already registered with another account"
                    }, status=400)
                otp_record = _get_verified_otp_record("email", new_email)
                if not otp_record:
                    return JsonResponse({
                        "success": False,
                        "message": "Email change requires OTP verification. Please verify your new email first."
                    }, status=400)
                user.email = new_email
                user.username = new_email.split('@')[0]
                otp_record.delete()

        if data.phone_number:
            new_phone = _normalize_phone(data.phone_number)
            if user.phone_number != new_phone:
                if CustomUser.objects.filter(phone_number=new_phone).exclude(id=user.id).exists():
                    return JsonResponse({
                        "success": False,
                        "message": "This phone number is already registered with another account"
                    }, status=400)
                otp_record = _get_verified_otp_record("phone", new_phone)
                if not otp_record:
                    return JsonResponse({
                        "success": False,
                        "message": "Phone change requires OTP verification. Please verify your new phone number first."
                    }, status=400)
                user.phone_number = new_phone
                otp_record.delete()

        user.save()

        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "fullname": user.fullname or "",
                "email": "" if _is_phone_otp_user(user) else user.email,
                "phone_number": user.phone_number or "",
                "can_update_phone": True,
                "can_update_email": True
            }
        }

    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error updating profile: {str(e)}"
        }, status=500)
