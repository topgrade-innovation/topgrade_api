# Import all view modules to register their endpoints
from . import (
    auth_views,
    category_view,
    program_view,
    bookmark_view,
    learning_view,
    carousel_view,
    area_of_interest_view,
    profile_view,
    enquiry_view,
    notification_api_view,
)

# Export the API instances for URL configuration
from .common import api
from .auth_views import auth_api
from .notification_api_view import router as notification_router

__all__ = [
    'api',
    'auth_api',
    'notification_router',
    'auth_views',
    'category_view',
    'program_view',
    'bookmark_view',
    'learning_view',
    'carousel_view',
    'area_of_interest_view',
    'profile_view',
    'enquiry_view',
    'notification_api_view',
]