"""
Helper functions for Firebase authentication and notifications in the API
"""
from topgrade_api.firebase_config import (
    verify_firebase_token, 
    get_user_by_phone,
    send_fcm_notification,
    send_fcm_multicast
)
from topgrade_api.models import FCMToken, Notification, NotificationLog
from django.utils import timezone

def validate_firebase_phone_auth(id_token):
    """
    Validate Firebase phone authentication token
    
    Args:
        id_token (str): Firebase ID token from Flutter client
        
    Returns:
        tuple: (success: bool, data: dict or error_message: str)
    """
    # Verify the Firebase token
    decoded_token = verify_firebase_token(id_token)
    
    if not decoded_token:
        return False, "Invalid or expired Firebase token"
    
    # Extract phone number from token
    phone_number = decoded_token.get('phone_number')
    
    if not phone_number:
        return False, "Phone number not found in token"
    
    # Remove country code prefix if needed (e.g., +91 -> return just the 10 digits)
    # You can customize this based on your needs
    clean_phone = phone_number.replace('+91', '').replace('+', '')
    
    return True, {
        'phone_number': clean_phone,
        'full_phone': phone_number,
        'uid': decoded_token.get('uid'),
        'firebase_data': decoded_token
    }

def register_fcm_token(user, token, device_type='android', device_id=None):
    """
    Register or update FCM token for a user
    
    Args:
        user: CustomUser instance
        token (str): FCM device token
        device_type (str): Device platform (android/ios/web)
        device_id (str): Optional device identifier
        
    Returns:
        FCMToken: Created or updated FCM token instance
    """
    fcm_token, created = FCMToken.objects.update_or_create(
        token=token,
        defaults={
            'user': user,
            'device_type': device_type,
            'device_id': device_id,
            'is_active': True,
            'last_used': timezone.now()
        }
    )
    return fcm_token

def send_notification_to_user(user, title, message, notification_type='general', data=None, image_url=None):
    """
    Send notification to a single user
    
    Args:
        user: CustomUser instance
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification
        data (dict): Additional data payload
        image_url (str): Optional image URL
        
    Returns:
        tuple: (success: bool, message: str)
    """
    # Get active FCM tokens for user
    tokens = FCMToken.objects.filter(user=user, is_active=True)
    
    if not tokens.exists():
        return False, "No active FCM tokens found for user"
    
    success_count = 0
    failed_count = 0
    
    for fcm_token in tokens:
        success, result = send_fcm_notification(
            token=fcm_token.token,
            title=title,
            body=message,
            data=data,
            image_url=image_url
        )
        
        if success:
            success_count += 1
            fcm_token.last_used = timezone.now()
            fcm_token.save()
        else:
            failed_count += 1
            # Deactivate token if it's invalid
            if "invalid" in result.lower() or "unregistered" in result.lower():
                fcm_token.is_active = False
                fcm_token.save()
    
    if success_count > 0:
        return True, f"Notification sent to {success_count} device(s)"
    else:
        return False, "Failed to send notification to any device"

def send_notification_to_users(users, title, message, notification_type='general', data=None, image_url=None, created_by=None, program=None):
    """
    Send notification to multiple users and create notification record
    
    Args:
        users: QuerySet or list of CustomUser instances
        title (str): Notification title
        message (str): Notification message
        notification_type (str): Type of notification
        data (dict): Additional data payload
        image_url (str): Optional image URL
        created_by: Admin user who created the notification
        program: Related program (optional)
        
    Returns:
        Notification: Created notification instance
    """
    # Create notification record
    notification = Notification.objects.create(
        title=title,
        message=message,
        notification_type=notification_type,
        data=data,
        image_url=image_url,
        created_by=created_by,
        program=program,
        total_recipients=len(users),
        status='pending'
    )
    
    # Add recipients
    notification.recipients.set(users)
    
    # Collect all active FCM tokens
    user_ids = [user.id for user in users]
    fcm_tokens = FCMToken.objects.filter(user_id__in=user_ids, is_active=True)
    
    if not fcm_tokens.exists():
        notification.status = 'failed'
        notification.save()
        return notification
    
    # Group tokens by batches (FCM supports up to 500 tokens per multicast)
    batch_size = 500
    tokens_list = list(fcm_tokens.values_list('token', flat=True))
    
    total_success = 0
    total_failed = 0
    failed_tokens = []
    invalid_tokens = []  # Only these will be deactivated
    
    for i in range(0, len(tokens_list), batch_size):
        batch_tokens = tokens_list[i:i + batch_size]
        success_count, failure_count, batch_failed, batch_invalid = send_fcm_multicast(
            tokens=batch_tokens,
            title=title,
            body=message,
            data=data,
            image_url=image_url
        )
        
        total_success += success_count
        total_failed += failure_count
        failed_tokens.extend(batch_failed)
        invalid_tokens.extend(batch_invalid)
    
    print(f"Notification sending complete: {total_success} success, {total_failed} failed, {len(invalid_tokens)} invalid tokens to deactivate")
    
    # Update notification status
    notification.sent_count = total_success
    notification.failed_count = total_failed
    notification.status = 'sent' if total_success > 0 else 'failed'
    notification.sent_at = timezone.now()
    notification.save()
    
    # Create notification logs for each user
    for user in users:
        user_tokens = fcm_tokens.filter(user=user)
        if user_tokens.exists():
            # Check if any of user's tokens succeeded
            user_token_values = list(user_tokens.values_list('token', flat=True))
            user_failed = any(token in failed_tokens for token in user_token_values)
            
            NotificationLog.objects.create(
                notification=notification,
                user=user,
                fcm_token=user_tokens.first(),
                status='failed' if user_failed else 'success',
                error_message='Failed to send notification' if user_failed else None
            )
    
    # Only deactivate tokens that are truly invalid (unregistered, etc)
    # Don't deactivate for temporary errors (network issues, etc)
    if invalid_tokens:
        deactivated_count = FCMToken.objects.filter(token__in=invalid_tokens).update(is_active=False)
        print(f"Deactivated {deactivated_count} invalid FCM tokens")
    
    # Update last_used for successful tokens
    successful_tokens = [t for t in tokens_list if t not in failed_tokens]
    if successful_tokens:
        FCMToken.objects.filter(token__in=successful_tokens).update(last_used=timezone.now())
    
    return notification
