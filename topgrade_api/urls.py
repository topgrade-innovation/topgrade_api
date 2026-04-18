from django.urls import path
from .views import api, auth_api

# Import views to register all endpoints
from . import views

# Add notification router to main API
from .views.notification_api_view import router as notification_router
api.add_router("/notifications", notification_router)

urlpatterns = [
    path("", api.urls),
    path("auth/", auth_api.urls),
]