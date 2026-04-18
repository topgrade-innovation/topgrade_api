from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.db.models import Count, Q
from topgrade_api.models import CustomUser, UserPurchase, Program, Category, UserCourseProgress
from .auth_view import admin_required

User = get_user_model()

@admin_required
def students_view(request):
    """Students view with statistics and student list"""
    # Handle POST request for adding new student
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'add_student':
            fullname = request.POST.get('fullname')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            area_of_intrest = request.POST.get('area_of_intrest')
            
            if fullname and email and phone_number:
                try:
                    # Add +91 prefix if not already present
                    if not phone_number.startswith('+'):
                        phone_number = f"+91{phone_number}"
                    
                    # Check if email already exists
                    if CustomUser.objects.filter(email=email).exists():
                        messages.error(request, 'A user with this email already exists.')
                    # Check if phone number already exists
                    elif CustomUser.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, 'A user with this phone number already exists.')
                    else:
                        # Generate password: Name (4 prefix) + Phone (4 suffix)
                        # Example: Dhinesh + 8610360491 => DHIN0491
                        name_prefix = fullname.replace(' ', '')[:4].upper()
                        phone_suffix = phone_number[-4:]
                        auto_password = f"{name_prefix}{phone_suffix}"
                        
                        # Create new student
                        student = CustomUser.objects.create_user(
                            email=email,
                            password=auto_password,
                            fullname=fullname,
                            phone_number=phone_number,
                            area_of_intrest=area_of_intrest,
                            role='student'
                        )
                        messages.success(request, f'Student "{fullname}" has been added successfully. Default password: {auto_password}')
                except Exception as e:
                    messages.error(request, f'Error creating student: {str(e)}')
            else:
                messages.error(request, 'Full name, email, and phone number are required.')
        
        elif form_type == 'edit_student':
            student_id = request.POST.get('student_id')
            fullname = request.POST.get('fullname')
            email = request.POST.get('email')
            phone_number = request.POST.get('phone_number')
            
            if student_id and fullname and email and phone_number:
                try:
                    # Add +91 prefix if not already present
                    if not phone_number.startswith('+'):
                        phone_number = f"+91{phone_number}"
                    
                    student = CustomUser.objects.get(id=student_id, role='student')
                    
                    # Check if email is being changed to one that already exists
                    if student.email != email and CustomUser.objects.filter(email=email).exists():
                        messages.error(request, 'A user with this email already exists.')
                    # Check if phone is being changed to one that already exists
                    elif student.phone_number != phone_number and CustomUser.objects.filter(phone_number=phone_number).exists():
                        messages.error(request, 'A user with this phone number already exists.')
                    else:
                        # Update student information
                        student.fullname = fullname
                        student.email = email
                        student.username = email  # Update username to match email
                        student.phone_number = phone_number
                        student.save()
                        messages.success(request, f'Student "{fullname}" has been updated successfully.')
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Student not found.')
                except Exception as e:
                    messages.error(request, f'Error updating student: {str(e)}')
            else:
                messages.error(request, 'All fields are required for updating student.')
        
        elif form_type == 'delete_student':
            student_id = request.POST.get('student_id')
            if student_id:
                try:
                    student = CustomUser.objects.get(id=student_id, role='student')
                    student_name = student.fullname or student.username or student.email
                    student.delete()
                    messages.success(request, f'Student "{student_name}" has been deleted successfully.')
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Student not found.')
                except Exception as e:
                    messages.error(request, f'Error deleting student: {str(e)}')
            else:
                messages.error(request, 'Student ID is required for deletion.')
        
        return redirect('dashboard:students')
    
    # Calculate statistics
    today = timezone.now().date()
    
    # Get all students
    all_students = CustomUser.objects.filter(role='student')
    total_students = all_students.count()
    
    # Students enrolled today
    today_enrolled = all_students.filter(date_joined__date=today).count()
    
    # Most popular area of interest
    popular_interest = all_students.exclude(area_of_intrest__isnull=True)\
                                 .exclude(area_of_intrest__exact='')\
                                 .values('area_of_intrest')\
                                 .annotate(count=Count('area_of_intrest'))\
                                 .order_by('-count')\
                                 .first()
    
    high_interest_area = popular_interest['area_of_intrest'] if popular_interest else 'N/A'
    high_interest_count = popular_interest['count'] if popular_interest else 0
    
    # Students with purchases (active learners)
    active_students = CustomUser.objects.filter(
        role='student',
        purchases__status='completed'
    ).distinct().count()
    
    # Get students list with pagination
    students_list = all_students.select_related().order_by('-date_joined')
    
    # Pagination
    paginator = Paginator(students_list, 10)  # Show 10 students per page
    page = request.GET.get('page')
    
    try:
        students = paginator.page(page)
    except PageNotAnInteger:
        students = paginator.page(1)
    except EmptyPage:
        students = paginator.page(paginator.num_pages)
    
    # Pagination range logic
    current_page = students.number
    total_pages = paginator.num_pages
    
    start_page = max(1, current_page - 2)
    end_page = min(total_pages, current_page + 2)
    
    if end_page - start_page < 4:
        if start_page == 1:
            end_page = min(total_pages, start_page + 4)
        elif end_page == total_pages:
            start_page = max(1, end_page - 4)
    
    page_range = range(start_page, end_page + 1)
    
    context = {
        'user': request.user,
        'students': students,
        'total_students': total_students,
        'today_enrolled': today_enrolled,
        'high_interest_area': high_interest_area,
        'high_interest_count': high_interest_count,
        'active_students': active_students,
        'page_range': page_range,
        'total_pages': total_pages,
        'current_page': current_page,
    }
    return render(request, 'dashboard/students.html', context)

@admin_required
def student_details_view(request, student_id):
    """Student details view"""
    try:
        student = CustomUser.objects.get(id=student_id, role='student')
    except CustomUser.DoesNotExist:
        messages.error(request, 'Student not found')
        return redirect('dashboard:students')
    
    # Get student's purchases/enrollments
    purchases = UserPurchase.objects.filter(user=student).select_related('program', 'program__category').order_by('-purchase_date')
    
    # Calculate statistics for this student
    total_enrollments = purchases.count()
    completed_enrollments = purchases.filter(status='completed').count()
    pending_enrollments = purchases.filter(status='pending').count()
    total_amount_paid = purchases.filter(status='completed').aggregate(
        total=models.Sum('amount_paid')
    )['total'] or 0
    
    # Calculate overall progress (based on completed vs total)
    total_courses = total_enrollments
    completed_courses = completed_enrollments
    overall_progress = int((completed_courses / total_courses * 100)) if total_courses > 0 else 0
    
    # Calculate time spent (placeholder values - can be enhanced with actual tracking)
    total_watch_hours = 0
    total_watch_minutes = 0
    learning_days = 0
    
    # Count days student has been active (days since first enrollment)
    if purchases.exists():
        first_purchase = purchases.last()
        learning_days = (timezone.now().date() - first_purchase.purchase_date.date()).days
    
    # Recent enrollments (last 10)
    recent_enrollments = purchases[:10]
    
    # Calculate completion rate
    completion_rate = int((completed_courses / total_courses * 100)) if total_courses > 0 else 0
    
    # Active enrollments (completed status)
    active_enrollments = completed_enrollments
    
    # Total spent
    total_spent = total_amount_paid
    
    # Average program rating (from enrolled programs)
    avg_program_rating = 0
    if purchases.exists():
        ratings = purchases.filter(program__program_rating__gt=0).aggregate(
            avg_rating=models.Avg('program__program_rating')
        )
        avg_program_rating = round(ratings['avg_rating'], 1) if ratings['avg_rating'] else 0
    
    # Progress data (placeholder - for future implementation with actual progress tracking)
    progress_data = []
    
    # Activity data (placeholder - for future implementation with actual activity tracking)
    activity_data = []
    
    context = {
        'user': request.user,
        'student': student,
        'purchases': purchases,
        'total_enrollments': total_enrollments,
        'completed_enrollments': completed_enrollments,
        'pending_enrollments': pending_enrollments,
        'total_amount_paid': total_amount_paid,
        'overall_progress': overall_progress,
        'completed_courses': completed_courses,
        'total_courses': total_courses,
        'total_watch_hours': total_watch_hours,
        'total_watch_minutes': total_watch_minutes,
        'learning_days': learning_days,
        'recent_enrollments': recent_enrollments,
        'completion_rate': completion_rate,
        'active_enrollments': active_enrollments,
        'total_spent': total_spent,
        'avg_program_rating': avg_program_rating,
        'progress_data': progress_data,
        'activity_data': activity_data,
    }
    return render(request, 'dashboard/student_details.html', context)

@admin_required
def assign_programs_view(request):
    """Assign programs to students view"""
    if request.method == 'POST':
        form_type = request.POST.get('form_type')
        
        if form_type == 'assign_program':
            student_id = request.POST.get('student_id')
            program_id = request.POST.get('program_id')
            amount_paid = request.POST.get('amount_paid', 0)
            is_goldpass = request.POST.get('is_goldpass') == 'on'
            
            if student_id and program_id:
                try:
                    student = CustomUser.objects.get(id=student_id, role='student')
                    program = Program.objects.get(id=program_id)
                    
                    # Check if student already has this program
                    existing_purchase = UserPurchase.objects.filter(
                        user=student,
                        program=program
                    ).first()
                    
                    if existing_purchase:
                        messages.warning(request, f'{student.fullname or student.email} is already enrolled in {program.title}')
                    else:
                        # Create new purchase/enrollment
                        purchase = UserPurchase.objects.create(
                            user=student,
                            program=program,
                            amount_paid=float(amount_paid) if amount_paid else 0.0,
                            status='completed',
                            purchase_date=timezone.now(),
                            require_goldpass=is_goldpass
                        )
                        goldpass_text = ' as GoldPass' if is_goldpass else ''
                        messages.success(request, f'Successfully assigned {program.title} to {student.fullname or student.email}{goldpass_text}')
                        
                except CustomUser.DoesNotExist:
                    messages.error(request, 'Student not found')
                except Program.DoesNotExist:
                    messages.error(request, 'Program not found')
                except Exception as e:
                    messages.error(request, f'Error assigning program: {str(e)}')
            else:
                messages.error(request, 'Student and program selection are required')
        
        elif form_type == 'toggle_goldpass':
            purchase_id = request.POST.get('purchase_id')
            if purchase_id:
                try:
                    purchase = UserPurchase.objects.get(id=purchase_id)
                    purchase.require_goldpass = not purchase.require_goldpass
                    purchase.save()
                    status_text = 'GoldPass' if purchase.require_goldpass else 'Regular'
                    messages.success(request, f'Successfully updated {purchase.program.title} to {status_text} for {purchase.user.fullname or purchase.user.email}')
                except UserPurchase.DoesNotExist:
                    messages.error(request, 'Assignment not found')
                except Exception as e:
                    messages.error(request, f'Error updating assignment: {str(e)}')
            else:
                messages.error(request, 'Assignment ID is required')
        
        elif form_type == 'remove_assignment':
            purchase_id = request.POST.get('purchase_id')
            if purchase_id:
                try:
                    purchase = UserPurchase.objects.get(id=purchase_id)
                    student_name = purchase.user.fullname or purchase.user.email
                    program_title = purchase.program.title
                    purchase.delete()
                    messages.success(request, f'Successfully removed {program_title} from {student_name}')
                except UserPurchase.DoesNotExist:
                    messages.error(request, 'Assignment not found')
                except Exception as e:
                    messages.error(request, f'Error removing assignment: {str(e)}')
            else:
                messages.error(request, 'Assignment ID is required for removal')
        
        elif form_type == 'mark_completed':
            assignment_id = request.POST.get('assignment_id')
            if assignment_id:
                try:
                    purchase = UserPurchase.objects.get(id=assignment_id)
                    
                    # Create or update UserCourseProgress as completed
                    course_progress, created = UserCourseProgress.objects.get_or_create(
                        user=purchase.user,
                        purchase=purchase,
                        defaults={
                            'is_completed': True,
                            'completion_percentage': 100.0,
                            'completed_at': timezone.now(),
                            'completed_topics': 0,
                            'total_topics': 0,
                        }
                    )
                    
                    if not created:
                        # Update existing progress to completed
                        course_progress.is_completed = True
                        course_progress.completion_percentage = 100.0
                        course_progress.completed_at = timezone.now()
                        course_progress.save()
                    
                    student_name = purchase.user.fullname or purchase.user.email
                    program_title = purchase.program.title
                    messages.success(request, f'Successfully marked {program_title} as completed for {student_name}')
                    
                except UserPurchase.DoesNotExist:
                    messages.error(request, 'Assignment not found')
                except Exception as e:
                    messages.error(request, f'Error marking as completed: {str(e)}')
            else:
                messages.error(request, 'Assignment ID is required')
        
        return redirect('dashboard:assign_programs')
    
    # GET request - show assignment form and data
    search_query = request.GET.get('search', '').strip()
    
    # Get all assignments with search functionality
    assignments_queryset = UserPurchase.objects.select_related('user', 'program', 'program__category').order_by('-purchase_date')
    
    if search_query:
        assignments_queryset = assignments_queryset.filter(
            Q(user__fullname__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(program__title__icontains=search_query) |
            Q(program__category__name__icontains=search_query)
        )
    
    # Pagination for assignments
    paginator = Paginator(assignments_queryset, 15)  # Show 15 assignments per page
    page = request.GET.get('page')
    
    try:
        assignments = paginator.page(page)
    except PageNotAnInteger:
        assignments = paginator.page(1)
    except EmptyPage:
        assignments = paginator.page(paginator.num_pages)
    
    # Calculate statistics
    total_assignments = UserPurchase.objects.count()
    active_assignments = UserPurchase.objects.filter(status='completed').count()
    total_students_with_programs = CustomUser.objects.filter(
        role='student',
        purchases__status='completed'
    ).distinct().count()
    
    # Get data for dropdowns
    students = CustomUser.objects.filter(role='student').order_by('fullname', 'email')
    programs = Program.objects.all().order_by('title')
    categories = Category.objects.all().order_by('name')
    
    context = {
        'user': request.user,
        'students': students,
        'programs': programs,
        'categories': categories,
        'assignments': assignments,
        'search_query': search_query,
        'total_assignments': total_assignments,
        'active_assignments': active_assignments,
        'total_students_with_programs': total_students_with_programs,
    }
    return render(request, 'dashboard/assign_programs.html', context)
