from django.shortcuts import render
from .auth_view import admin_required


@admin_required
def chat_view(request):
    """Chat view for dashboard"""
    context = {
        'user': request.user,
    }
    return render(request, 'dashboard/coming_soon.html', context)