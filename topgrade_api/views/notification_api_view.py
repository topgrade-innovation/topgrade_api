"""
API endpoints for Firebase Push Notifications
Mobile apps can use these endpoints to interact with the notification system
"""
from ninja import Router
from django.utils import timezone
from topgrade_api.models import FCMToken, Notification, NotificationLog
from topgrade_api.utils.firebase_helper import register_fcm_token as register_token_helper
from topgrade_api.schemas import RegisterFCMTokenSchema, MarkNotificationReadSchema
from topgrade_api.views.common import AuthBearer

router = Router(tags=["Notifications"])

# Endpoints

@router.post("/register-fcm-token", auth=AuthBearer())
def register_fcm_token_api(request, payload: RegisterFCMTokenSchema):
    """
    Register or update FCM token for the authenticated user
    
    Mobile app should call this endpoint after user login with their FCM device token
    
    Request Body:
    {
        "token": "fcm_device_token_here",
        "device_type": "android",  // or "ios", "web"
        "device_id": "optional_device_identifier"
    }
    """
    try:
        fcm_token = register_token_helper(
            user=request.auth,
            token=payload.token,
            device_type=payload.device_type,
            device_id=payload.device_id
        )
        
        return {
            "success": True,
            "message": "FCM token registered successfully",
            "data": {
                "token_id": fcm_token.id,
                "device_type": fcm_token.device_type,
                "is_active": fcm_token.is_active
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error registering FCM token: {str(e)}"
        }

@router.post("/mark-notification-read", auth=AuthBearer())
def mark_notification_read(request, payload: MarkNotificationReadSchema):
    """
    Mark a notification as read by the user
    
    Mobile app should call this when user opens/views a notification
    
    Request Body:
    {
        "notification_id": 123
    }
    """
    try:
        log = NotificationLog.objects.get(
            notification_id=payload.notification_id,
            user=request.auth
        )
        
        if not log.is_read:
            log.is_read = True
            log.read_at = timezone.now()
            log.save()
        
        return {
            "success": True,
            "message": "Notification marked as read",
            "data": {
                "notification_id": log.notification.id,
                "read_at": log.read_at.isoformat()
            }
        }
    except NotificationLog.DoesNotExist:
        return {
            "success": False,
            "message": "Notification not found or not sent to this user"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking notification as read: {str(e)}"
        }

@router.get("/notifications", auth=AuthBearer())
def get_user_notifications(request, limit: int = 20, offset: int = 0):
    """
    Get user's notification history with pagination
    
    Query Parameters:
    - limit: Number of notifications to return (default: 20, max: 100)
    - offset: Pagination offset (default: 0)
    
    Returns list of notifications sent to the authenticated user
    """
    try:
        # Limit maximum to 100
        limit = min(limit, 100)
        
        logs = NotificationLog.objects.filter(
            user=request.auth
        ).select_related('notification').order_by('-sent_at')[offset:offset+limit]
        
        total_count = NotificationLog.objects.filter(user=request.auth).count()
        unread_count = NotificationLog.objects.filter(user=request.auth, is_read=False).count()
        
        notifications = []
        for log in logs:
            notifications.append({
                "id": log.notification.id,
                "title": log.notification.title,
                "message": log.notification.message,
                "notification_type": log.notification.notification_type,
                "image_url": log.notification.image_url,
                "data": log.notification.data,
                "is_read": log.is_read,
                "sent_at": log.sent_at.isoformat(),
                "read_at": log.read_at.isoformat() if log.read_at else None
            })
        
        return {
            "success": True,
            "data": {
                "notifications": notifications,
                "pagination": {
                    "total_count": total_count,
                    "unread_count": unread_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error fetching notifications: {str(e)}"
        }

@router.get("/notifications/unread-count", auth=AuthBearer())
def get_unread_count(request):
    """
    Get count of unread notifications for the authenticated user
    
    Useful for showing notification badges in mobile app
    """
    try:
        unread_count = NotificationLog.objects.filter(
            user=request.auth,
            is_read=False
        ).count()
        
        return {
            "success": True,
            "data": {
                "unread_count": unread_count
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting unread count: {str(e)}"
        }

@router.post("/mark-all-read", auth=AuthBearer())
def mark_all_notifications_read(request):
    """
    Mark all notifications as read for the authenticated user
    """
    try:
        updated_count = NotificationLog.objects.filter(
            user=request.auth,
            is_read=False
        ).update(
            is_read=True,
            read_at=timezone.now()
        )
        
        return {
            "success": True,
            "message": f"Marked {updated_count} notifications as read",
            "data": {
                "updated_count": updated_count
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error marking notifications as read: {str(e)}"
        }

@router.delete("/fcm-token", auth=AuthBearer())
def delete_fcm_token(request, token: str):
    """
    Delete/deactivate an FCM token
    
    Mobile app should call this on logout or when user disables notifications
    
    Query Parameters:
    - token: FCM token to delete
    """
    try:
        fcm_token = FCMToken.objects.get(
            user=request.auth,
            token=token
        )
        
        # Deactivate instead of delete to keep history
        fcm_token.is_active = False
        fcm_token.save()
        
        return {
            "success": True,
            "message": "FCM token deactivated successfully"
        }
    except FCMToken.DoesNotExist:
        return {
            "success": False,
            "message": "FCM token not found"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error deleting FCM token: {str(e)}"
        }

@router.get("/fcm-tokens", auth=AuthBearer())
def get_user_fcm_tokens(request):
    """
    Get all FCM tokens registered for the authenticated user
    
    Useful for managing multiple devices
    """
    try:
        tokens = FCMToken.objects.filter(user=request.auth).order_by('-created_at')
        
        token_list = []
        for token in tokens:
            token_list.append({
                "id": token.id,
                "device_type": token.device_type,
                "device_id": token.device_id,
                "is_active": token.is_active,
                "last_used": token.last_used.isoformat() if token.last_used else None,
                "created_at": token.created_at.isoformat()
            })
        
        return {
            "success": True,
            "data": {
                "tokens": token_list,
                "total_count": len(token_list),
                "active_count": sum(1 for t in token_list if t['is_active'])
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error fetching FCM tokens: {str(e)}"
        }
