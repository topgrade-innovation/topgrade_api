from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def admin_required(view_func):
    """
    Decorator to ensure only admin users (superusers) can access dashboard views
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('/dashboard/signin/')
        
        if not request.user.is_superuser:
            messages.error(request, 'You are not authorized to access the dashboard.')
            return redirect('/dashboard/signin/')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def signin_view(request):
    """
    Custom login view for dashboard - only allows admin users (superusers)
    """
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        # Use AdminOnlyBackend for authentication
        user = authenticate(request, username=email, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('/dashboard/')
        else:
            messages.error(request, 'Invalid credentials or you are not authorized to access the dashboard.')
    
    return render(request, 'dashboard/signin.html')


def dashboard_logout(request):
    """
    Logout view for dashboard
    """
    logout(request)
    return redirect('/dashboard/signin/')