"""
Firebase Admin SDK Configuration for OTP Verification and Cloud Messaging
"""
import firebase_admin
from firebase_admin import credentials, auth, messaging
from django.conf import settings
import os

# Initialize Firebase Admin SDK
def initialize_firebase():
    """
    Initialize Firebase Admin SDK with service account credentials
    """
    if not firebase_admin._apps:
        # Path to your Firebase service account key JSON file
        cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH', 'firebase-credentials.json')
        
        try:
            cred = credentials.Certificate(cred_path)
            firebase_admin.initialize_app(cred)
            print("Firebase Admin SDK initialized successfully")
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            # If credentials file not found, you can initialize without credentials for development
            # firebase_admin.initialize_app()

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token from Flutter app
    
    Args:
        id_token (str): Firebase ID token from Flutter client
        
    Returns:
        dict: Decoded token containing user info (phone_number, uid, etc.)
        None: If token is invalid
    """
    try:
        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except auth.InvalidIdTokenError:
        print("Invalid Firebase ID token")
        return None
    except auth.ExpiredIdTokenError:
        print("Firebase ID token has expired")
        return None
    except Exception as e:
        print(f"Error verifying Firebase token: {e}")
        return None

def get_user_by_phone(phone_number):
    """
    Get Firebase user by phone number
    
    Args:
        phone_number (str): Phone number with country code (e.g., +919876543210)
        
    Returns:
        UserRecord: Firebase user record
        None: If user not found
    """
    try:
        user = auth.get_user_by_phone_number(phone_number)
        return user
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        print(f"Error getting user by phone: {e}")
        return None

def verify_phone_number(phone_number, verification_code):
    """
    Note: Firebase Admin SDK doesn't directly verify OTP codes.
    OTP verification happens on the client side (Flutter app).
    
    The server only verifies the ID token that the client receives
    after successful OTP verification.
    
    This function is kept for reference/documentation purposes.
    """
    pass

def send_fcm_notification(token, title, body, data=None, image_url=None):
    """
    Send a push notification via Firebase Cloud Messaging to a single device
    
    Args:
        token (str): FCM device token
        title (str): Notification title
        body (str): Notification body/message
        data (dict): Additional data payload (optional)
        image_url (str): URL of image to display in notification (optional)
        
    Returns:
        tuple: (success: bool, message_id or error: str)
    """
    try:
        # Build notification
        notification = messaging.Notification(
            title=title,
            body=body,
            image=image_url if image_url else None
        )
        
        # Build message
        message = messaging.Message(
            notification=notification,
            data=data if data else {},
            token=token,
            android=messaging.AndroidConfig(
                priority='high',
                notification=messaging.AndroidNotification(
                    sound='default',
                    channel_id='default'
                )
            ),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        badge=1
                    )
                )
            )
        )
        
        # Send message
        response = messaging.send(message)
        return True, response
        
    except messaging.UnregisteredError:
        return False, "Token is invalid or unregistered"
    except messaging.SenderIdMismatchError:
        return False, "Token does not match sender ID"
    except Exception as e:
        return False, str(e)

def send_fcm_multicast(tokens, title, body, data=None, image_url=None):
    """
    Send a push notification via Firebase Cloud Messaging to multiple devices
    Uses send_each for Firebase Admin SDK v7+
    
    Args:
        tokens (list): List of FCM device tokens
        title (str): Notification title
        body (str): Notification body/message
        data (dict): Additional data payload (optional)
        image_url (str): URL of image to display in notification (optional)
        
    Returns:
        tuple: (success_count: int, failure_count: int, failed_tokens: list, invalid_tokens: list)
    """
    try:
        # Ensure data is a dict with string values only
        if data:
            data = {str(k): str(v) for k, v in data.items()}
        else:
            data = {}
        
        # Build individual messages for each token
        messages = []
        for token in tokens:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url if image_url else None
                ),
                data=data,
                token=token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        channel_id='default'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            sound='default',
                            badge=1
                        )
                    )
                )
            )
            messages.append(message)
        
        # Send all messages using send_each
        response = messaging.send_each(messages)
        
        # Collect failed tokens and identify which ones are truly invalid
        failed_tokens = []
        invalid_tokens = []  # Only these should be deactivated
        success_count = 0
        failure_count = 0
        
        for idx, send_response in enumerate(response.responses):
            if send_response.success:
                success_count += 1
            else:
                failure_count += 1
                token = tokens[idx]
                failed_tokens.append(token)
                
                # Check if error is due to invalid/unregistered token
                if send_response.exception:
                    error_msg = str(send_response.exception)
                    print(f"Token {token[:20]}... failed with error: {error_msg}")
                    
                    # Only mark as invalid for these specific errors
                    if any(err in error_msg.lower() for err in [
                        'unregistered', 'invalid-registration-token', 
                        'registration-token-not-registered', 'invalid-argument',
                        'not-found'
                    ]):
                        invalid_tokens.append(token)
                else:
                    # If no specific error, it might be temporary (network, etc)
                    print(f"Token {token[:20]}... failed with unknown error")
        
        print(f"FCM Send: {success_count} success, {failure_count} failed, {len(invalid_tokens)} invalid tokens")
        
        return success_count, failure_count, failed_tokens, invalid_tokens
        
    except Exception as e:
        print(f"Error sending notifications: {e}")
        import traceback
        traceback.print_exc()
        return 0, len(tokens), tokens, []  # Don't deactivate on general errors
