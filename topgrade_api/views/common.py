"""
Common utilities and shared components for API views
"""
from ninja import NinjaAPI
from ninja.security import HttpBearer
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.contrib.auth import get_user_model

User = get_user_model()

class AuthBearer(HttpBearer):
    """
    Common JWT authentication for all API endpoints
    """
    def authenticate(self, request, token):
        try:
            # Validate the token
            UntypedToken(token)
            # Get user from token
            from rest_framework_simplejwt.tokens import AccessToken
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            user = User.objects.get(id=user_id)
            return user
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None

# Common API instance for general endpoints
api = NinjaAPI(version="1.0.0", title="General API")