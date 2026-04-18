from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
import calendar
from topgrade_api.models import Category, Program, UserPurchase, CustomUser
from .auth_view import admin_required

User = get_user_model()

@admin_required
def dashboard_home(request):
    """
    Dashboard home view with comprehensive analytics - only accessible by admin users (superusers)
    """
    # Date calculations
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    last_30_days = today - timedelta(days=30)
    last_7_days = today - timedelta(days=7)
    
    # Students Analytics
    all_students = User.objects.filter(role='student')
    total_students = all_students.count()
    new_students_today = all_students.filter(date_joined__date=today).count()
    new_students_this_month = all_students.filter(date_joined__month=current_month, date_joined__year=current_year).count()
    active_students = User.objects.filter(role='student', purchases__status='completed').distinct().count()
    
    # Programs Analytics
    total_programs = Program.objects.count()
    total_categories = Category.objects.count()
    advanced_programs = Program.objects.filter(category__name='Advanced Program').count()
    best_seller_programs = Program.objects.filter(is_best_seller=True).count()
    
    # Enrollment Analytics
    all_purchases = UserPurchase.objects.all()
    total_enrollments = all_purchases.count()
    completed_enrollments = all_purchases.filter(status='completed').count()
    pending_enrollments = all_purchases.filter(status='pending').count()
    enrollments_today = all_purchases.filter(purchase_date__date=today).count()
    enrollments_this_month = all_purchases.filter(purchase_date__month=current_month, purchase_date__year=current_year).count()
    
    # Revenue Analytics
    total_revenue = all_purchases.filter(status='completed').aggregate(total=Sum('amount_paid'))['total'] or 0
    revenue_this_month = all_purchases.filter(
        status='completed', 
        purchase_date__month=current_month, 
        purchase_date__year=current_year
    ).aggregate(total=Sum('amount_paid'))['total'] or 0
    
    # Average revenue per enrollment
    avg_revenue_per_enrollment = total_revenue / completed_enrollments if completed_enrollments > 0 else 0
    
    # Monthly enrollment trends (last 12 months)
    enrollment_trends = []
    for i in range(11, -1, -1):
        date = today.replace(day=1) - timedelta(days=30*i)
        month_enrollments = all_purchases.filter(
            purchase_date__month=date.month, 
            purchase_date__year=date.year
        ).count()
        enrollment_trends.append({
            'month': calendar.month_abbr[date.month],
            'count': month_enrollments
        })
    
    # Weekly enrollment trends (last 4 weeks)
    weekly_trends = []
    for i in range(3, -1, -1):
        week_start = today - timedelta(days=today.weekday() + 7*i)
        week_end = week_start + timedelta(days=6)
        week_enrollments = all_purchases.filter(
            purchase_date__date__range=[week_start, week_end]
        ).count()
        weekly_trends.append({
            'week': f"Week {4-i}",
            'count': week_enrollments
        })
    
    # Top performing programs
    top_programs = Program.objects.annotate(
        enrollment_count=Count('purchases')
    ).order_by('-enrollment_count')[:5]
    
    # Recent enrollments
    recent_enrollments = UserPurchase.objects.select_related('user', 'program').order_by('-purchase_date')[:10]
    
    # Program category distribution
    category_distribution = Category.objects.annotate(
        program_count=Count('programs')
    ).values('name', 'program_count')
    
    # Student area of interest distribution
    interest_distribution = all_students.exclude(
        Q(area_of_intrest__isnull=True) | Q(area_of_intrest__exact='')
    ).values('area_of_intrest').annotate(count=Count('area_of_intrest')).order_by('-count')[:5]
    
    # Revenue by program
    revenue_by_program = Program.objects.annotate(
        revenue=Sum('purchases__amount_paid', filter=Q(purchases__status='completed'))
    ).order_by('-revenue')[:5]
    
    # Calculate growth rates
    last_month = today.replace(day=1) - timedelta(days=1)
    last_month_enrollments = all_purchases.filter(
        purchase_date__month=last_month.month, 
        purchase_date__year=last_month.year
    ).count()
    
    if last_month_enrollments > 0:
        enrollment_growth = round(((enrollments_this_month - last_month_enrollments) / last_month_enrollments) * 100, 1)
    else:
        enrollment_growth = 100 if enrollments_this_month > 0 else 0
    
    # Students registered last month
    last_month_students = all_students.filter(
        date_joined__month=last_month.month, 
        date_joined__year=last_month.year
    ).count()
    
    if last_month_students > 0:
        student_growth = round(((new_students_this_month - last_month_students) / last_month_students) * 100, 1)
    else:
        student_growth = 100 if new_students_this_month > 0 else 0
    
    context = {
        'user': request.user,
        # Student metrics
        'total_students': total_students,
        'new_students_today': new_students_today,
        'new_students_this_month': new_students_this_month,
        'active_students': active_students,
        'student_growth': student_growth,
        
        # Program metrics
        'total_programs': total_programs,
        'total_categories': total_categories,
        'advanced_programs': advanced_programs,
        'best_seller_programs': best_seller_programs,
        
        # Enrollment metrics
        'total_enrollments': total_enrollments,
        'completed_enrollments': completed_enrollments,
        'pending_enrollments': pending_enrollments,
        'enrollments_today': enrollments_today,
        'enrollments_this_month': enrollments_this_month,
        'enrollment_growth': enrollment_growth,
        
        # Revenue metrics
        'total_revenue': total_revenue,
        'revenue_this_month': revenue_this_month,
        'avg_revenue_per_enrollment': avg_revenue_per_enrollment,
        
        # Charts data
        'enrollment_trends': enrollment_trends,
        'weekly_trends': weekly_trends,
        'category_distribution': list(category_distribution),
        'interest_distribution': list(interest_distribution),
        'revenue_by_program': revenue_by_program,
        
        # Tables data
        'top_programs': top_programs,
        'recent_enrollments': recent_enrollments,
    }
    return render(request, 'dashboard/dashboard.html', context)