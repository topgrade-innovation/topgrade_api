"""
Profile view for mobile app - returns student-related data
"""
from django.http import JsonResponse
from django.db.models import Count, Avg, Sum, Q
from topgrade_api.models import CustomUser, UserPurchase, UserBookmark, UserCourseProgress, UserTopicProgress
from topgrade_api.schemas import UpdateProfileSchema
from .common import api, AuthBearer

@api.get("/profile", auth=AuthBearer())
def get_user_profile(request):
    """
    Get comprehensive user profile data for mobile app
    Returns user info, purchase stats, bookmarks, and learning progress
    """
    user = request.auth
    
    try:
        # Check if user registered via phone OTP (has temp email pattern)
        is_phone_otp_user = user.email and user.email.startswith('phone_') and user.email.endswith('@tempuser.com')
        
        # Basic user information
        profile_data = {
            "user_info": {
                "id": user.id,
                "email": user.email,
                "fullname": user.fullname or "",
                "phone_number": user.phone_number or "",
                "can_update_phone": not is_phone_otp_user,  # Indicate if phone can be updated
                "can_update_email": is_phone_otp_user,  # Phone OTP users can update email
                "registration_type": "phone_otp" if is_phone_otp_user else "email"  # Helpful for mobile app
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
        from datetime import datetime, timedelta
        from django.utils import timezone
        seven_days_ago = timezone.now() - timedelta(days=7)
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


@api.put("/profile/update", auth=AuthBearer())
def update_user_profile(request, data: UpdateProfileSchema):
    """
    Update user profile information
    Phone number can only be updated by users who registered via email.
    Users who registered via phone OTP cannot update their phone number.
    """
    user = request.auth
    
    try:
        # Check if user registered via phone OTP (has temp email pattern)
        is_phone_otp_user = user.email and user.email.startswith('phone_') and user.email.endswith('@tempuser.com')
        
        # Update allowed fields
        if data.fullname:
            user.fullname = data.fullname
            
        if data.email:
            if not is_phone_otp_user:
                return JsonResponse({
                    "success": False,
                    "message": "Email cannot be updated for accounts registered via email"
                }, status=400)
            else:
                # Check if email is already used by another user
                if CustomUser.objects.filter(email=data.email).exclude(id=user.id).exists():
                    return JsonResponse({
                        "success": False,
                        "message": "This email is already registered with another account"
                    }, status=400)
                user.email = data.email
            
        if data.phone_number:
            if is_phone_otp_user:
                return JsonResponse({
                    "success": False,
                    "message": "Phone number cannot be updated for accounts registered via phone OTP"
                }, status=400)
            else:
                # Check if phone number is already used by another user
                if CustomUser.objects.filter(phone_number=data.phone_number).exclude(id=user.id).exists():
                    return JsonResponse({
                        "success": False,
                        "message": "This phone number is already registered with another account"
                    }, status=400)
                user.phone_number = data.phone_number
        
        user.save()
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "fullname": user.fullname,
                "email": user.email,
                "phone_number": user.phone_number,
                "can_update_phone": not is_phone_otp_user,
                "can_update_email": is_phone_otp_user
            }
        }
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error updating profile: {str(e)}"
        }, status=500)