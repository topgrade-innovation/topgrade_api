from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class AdminOnlyBackend(BaseBackend):
    """
    Custom authentication backend that only allows admin users (superusers) to authenticate
    for dashboard access.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to find user by email (since we use email as username)
            user = User.objects.get(email=username)
            
            # Check if password is correct and user is a superuser
            if user.check_password(password) and user.is_superuser:
                return user
        except User.DoesNotExist:
            return None
        
        return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            # Only return user if they are a superuser
            if user.is_superuser:
                return user
        except User.DoesNotExist:
            return None
        
        return None