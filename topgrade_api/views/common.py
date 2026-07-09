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
            # Reject tokens issued before the user's password was last changed
            # (e.g. an admin reset it) so the user is forced to re-login.
            if not is_token_valid_for_user(user, access_token):
                return None
            return user
        except (InvalidToken, TokenError, User.DoesNotExist):
            return None


def is_token_valid_for_user(user, token):
    """
    Return False if the token was issued before the user's password was last
    changed. Used to invalidate all existing access/refresh tokens on an
    admin-initiated password change.
    """
    password_changed_at = getattr(user, 'password_changed_at', None)
    if not password_changed_at:
        return True
    issued_at = token.payload.get('iat')
    if issued_at is None:
        return True
    return issued_at >= int(password_changed_at.timestamp())

# Common API instance for general endpoints
api = NinjaAPI(version="1.0.0", title="General API")