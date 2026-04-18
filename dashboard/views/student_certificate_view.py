from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from topgrade_api.models import CustomUser, UserCourseProgress, UserCertificate
from .auth_view import admin_required
from dashboard.utils import generate_certificate_pdf, generate_bulk_certificates
from dashboard.tasks import send_certificates_email_task


@admin_required
@require_POST
def generate_certificate_ajax(request):
    """AJAX endpoint for generating certificates"""
    course_progress_id = request.POST.get('course_progress_id')
    
    if not course_progress_id:
        return JsonResponse({
            'success': False,
            'message': 'Course progress ID is required'
        }, status=400)
    
    try:
        course_progress = UserCourseProgress.objects.get(id=course_progress_id, is_completed=True)
        
        # Check if user purchase requires goldpass to determine certificate types
        require_goldpass = course_progress.purchase.require_goldpass
        
        # Generate a single certificate number for all certificates
        import uuid
        base_certificate_number = f"CERT-{uuid.uuid4().hex[:8].upper()}"
        
        # Generate bulk certificates
        certificates = generate_bulk_certificates(
            user=course_progress.user,
            program=course_progress.purchase.program,
            base_certificate_number=base_certificate_number,
            completion_date=course_progress.completed_at,
            purchase_date=course_progress.purchase.purchase_date,
            include_placement=require_goldpass
        )
        
        # Save each certificate to the database
        certificates_created = []
        certificates_data = []
        for cert_type, pdf_file in certificates.items():
            certificate, created = UserCertificate.objects.get_or_create(
                user=course_progress.user,
                course_progress=course_progress,
                program=course_progress.purchase.program,
                certificate_type=cert_type,
                defaults={
                    'status': 'pending',
                    'certificate_number': base_certificate_number,
                }
            )
            
            # Save the PDF file
            certificate.certificate_file.save(
                f"{cert_type}_certificate_{base_certificate_number}.pdf",
                pdf_file,
                save=True
            )
            certificates_created.append(certificate.get_certificate_type_display())
            certificates_data.append({
                'type': cert_type,
                'url': certificate.certificate_file.url,
                'display_name': certificate.get_certificate_type_display()
            })
        
        student_name = course_progress.user.fullname or course_progress.user.email
        cert_count = len(certificates_created)
        cert_list = ', '.join(certificates_created)
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully generated {cert_count} certificates for {student_name}: {cert_list}',
            'certificates': certificates_data,
            'certificate_number': base_certificate_number,
            'require_goldpass': require_goldpass
        })
        
    except UserCourseProgress.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Course progress not found or not completed'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error generating certificates: {str(e)}'
        }, status=500)


@admin_required
@require_POST
def send_certificate_ajax(request):
    """AJAX endpoint for sending certificates"""
    course_progress_id = request.POST.get('course_progress_id')
    
    if not course_progress_id:
        return JsonResponse({
            'success': False,
            'message': 'Course progress ID is required'
        }, status=400)
    
    try:
        course_progress = UserCourseProgress.objects.get(id=course_progress_id, is_completed=True)
        
        # Check if certificates exist
        certificates = UserCertificate.objects.filter(
            user=course_progress.user,
            course_progress=course_progress,
            program=course_progress.purchase.program,
        )
        
        if not certificates.exists():
            return JsonResponse({
                'success': False,
                'message': 'No certificates found for this student'
            }, status=404)
        
        # Check if already sent
        pending_certificates = certificates.filter(status='pending')
        if not pending_certificates.exists():
            return JsonResponse({
                'success': True,
                'message': f'All certificates already sent to {course_progress.user.fullname or course_progress.user.email}',
                'already_sent': True
            })
        
        # Update certificate status to 'sent' and set sent_date
        updated_count = 0
        for certificate in pending_certificates:
            certificate.status = 'sent'
            certificate.sent_date = timezone.now()
            certificate.save()
            updated_count += 1
        
        # Trigger Celery task to send email in background
        send_certificates_email_task.delay(course_progress_id)
        
        student_name = course_progress.user.fullname or course_progress.user.email
        sent_date = timezone.now().strftime('%d/%m/%Y')
        
        return JsonResponse({
            'success': True,
            'message': f'Certificates marked as sent and email is being sent to {student_name}',
            'sent_date': sent_date,
            'email_queued': True
        })
        
    except UserCourseProgress.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Course progress not found or not completed'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending certificates: {str(e)}'
        }, status=500)


@admin_required
def student_certificates_view(request):
    """Student certificates view - List students who completed courses"""
    
    # GET request - display list of completed courses
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', 'all')
    
    # Get all completed course progress records
    completed_courses = UserCourseProgress.objects.filter(
        is_completed=True
    ).select_related(
        'user', 'purchase__program', 'purchase__program__category'
    ).order_by('-completed_at')
    
    # Apply search filter
    if search_query:
        completed_courses = completed_courses.filter(
            Q(user__fullname__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(purchase__program__title__icontains=search_query)
        )
    
    # Annotate with certificate information
    completed_courses_with_certs = []
    for course_progress in completed_courses:
        certificates = UserCertificate.objects.filter(course_progress=course_progress)
        
        if certificates.exists():
            has_certificate = True
            # Get the status based on certificates (if any are sent, show sent, else pending)
            sent_certificates = certificates.filter(status='sent')
            if sent_certificates.exists():
                certificate_status = 'sent'
                certificate_sent_date = sent_certificates.first().sent_date
            else:
                certificate_status = 'pending'
                certificate_sent_date = None
            
            # Use the first certificate's number (they should all have the same number)
            certificate_number = certificates.first().certificate_number
            certificates_list = certificates
        else:
            has_certificate = False
            certificate_status = 'not_issued'
            certificate_number = None
            certificate_sent_date = None
            certificates_list = None
        
        completed_courses_with_certs.append({
            'course_progress': course_progress,
            'has_certificate': has_certificate,
            'certificate_status': certificate_status,
            'certificate_number': certificate_number,
            'certificate_sent_date': certificate_sent_date,
            'certificates_list': certificates_list,
            'require_goldpass': course_progress.purchase.require_goldpass,
        })
    
    # Apply status filter
    if status_filter == 'sent':
        completed_courses_with_certs = [item for item in completed_courses_with_certs if item['certificate_status'] == 'sent']
    elif status_filter == 'pending':
        completed_courses_with_certs = [item for item in completed_courses_with_certs if item['certificate_status'] in ['pending', 'not_issued']]
    
    # Calculate statistics
    total_completed = completed_courses.count()
    total_certificates_sent = UserCertificate.objects.filter(status='sent').count()
    total_certificates_pending = total_completed - total_certificates_sent
    
    # Pagination
    paginator = Paginator(completed_courses_with_certs, 15)  # Show 15 per page
    page = request.GET.get('page')
    
    try:
        completed_courses_page = paginator.page(page)
    except PageNotAnInteger:
        completed_courses_page = paginator.page(1)
    except EmptyPage:
        completed_courses_page = paginator.page(paginator.num_pages)
    
    # Pagination range logic
    current_page = completed_courses_page.number
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
        'completed_courses': completed_courses_page,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_completed': total_completed,
        'total_certificates_sent': total_certificates_sent,
        'total_certificates_pending': total_certificates_pending,
        'page_range': page_range,
        'total_pages': total_pages,
        'current_page': current_page,
    }
    return render(request, 'dashboard/student_certificates.html', context)
