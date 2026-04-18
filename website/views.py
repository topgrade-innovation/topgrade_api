from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from topgrade_api.models import Category, Program, Carousel, Testimonial, ProgramEnquiry, DeleteAccountRequest

# Create your views here.
def index(request):
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()
    # Get active testimonials for display
    testimonials = Testimonial.objects.filter(is_active=True).order_by('created_at')
    
    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
        'testimonials': testimonials
    }
    return render(request, 'website/index.html', context)

def about(request):
    """About page"""
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()
    
    # Get 8 recent active gallery images for "Life at TopGrade" section
    from topgrade_api.models import Gallery
    gallery_images = Gallery.objects.filter(is_active=True).order_by('-created_at')[:8]

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
        'gallery_images': gallery_images,
    }
    return render(request, 'website/about.html', context)

def blog(request):
    """Blog page"""
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/blog.html', context)

def programs(request):
    """Programs page - shows first available program or specific program"""
    # Get all regular programs
    programs_queryset = Program.get_regular_programs()
    
    # Get specific program ID from URL parameter if provided
    program_id = request.GET.get('id')
    
    if program_id:
        try:
            program = programs_queryset.get(id=program_id)
        except Program.DoesNotExist:
            # If program not found, get first available program
            program = programs_queryset.first()
    else:
        # Get first available program
        program = programs_queryset.first()
    
    context = {
        'program': program,
        'programs': programs_queryset,  # All programs for any navigation needs
    }
    return render(request, 'website/programs.html', context)

def advance_programs(request):
    """Advanced programs listing page with filtering and pagination"""
    # Get query parameters
    search_query = request.GET.get('search')
    sort_by = request.GET.get('sort', '-created_at')
    
    # Base queryset - advanced programs only
    programs_queryset = Program.get_advanced_programs()
    
    # Apply search filter
    if search_query:
        programs_queryset = programs_queryset.filter(
            title__icontains=search_query
        )
    
    # Apply sorting
    valid_sort_options = ['-created_at', 'created_at', 'title', '-title', 'price', '-price', '-program_rating']
    if sort_by in valid_sort_options:
        programs_queryset = programs_queryset.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(programs_queryset, 12)  # 12 programs per page
    page_number = request.GET.get('page')
    programs = paginator.get_page(page_number)
    
    context = {
        'programs': programs,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_programs': programs_queryset.count(),
        'is_advanced': True,  # Flag to identify this is advanced programs page
    }
    return render(request, 'website/advance_programs.html', context)

def contact(request):
    """Contact page with form submission handling"""
    success_message = None
    error_message = None
    
    if request.method == 'POST':
        # Get form data
        full_name = request.POST.get('full_name', '').strip()
        email = request.POST.get('email', '').strip()
        contact_no = request.POST.get('contact_no', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        
        # Basic validation
        if not all([full_name, email, subject, message]):
            error_message = "Please fill in all required fields."
        elif len(full_name) < 2:
            error_message = "Please enter a valid full name."
        elif len(subject) < 3:
            error_message = "Subject must be at least 3 characters long."
        elif len(message) < 5:
            error_message = "Message must be at least 5 characters long."
        elif contact_no and len(contact_no) < 10:
            error_message = "Please enter a valid contact number (minimum 10 digits)."
        else:
            # Validate email format
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError
            try:
                validate_email(email)
            except ValidationError:
                error_message = "Please enter a valid email address."
            
            if not error_message:
                try:
                    # Import Contact model
                    from topgrade_api.models import Contact
                    
                    # Create contact submission
                    contact_submission = Contact.objects.create(
                        full_name=full_name,
                        email=email,
                        contact_no=contact_no if contact_no else None,
                        subject=subject,
                        message=message
                    )
                    
                    success_message = "Thank you for contacting us! We'll get back to you within 24 hours."
                    
                    # Optional: Send email notification to admin
                    # You can add email functionality here
                    
                except Exception as e:
                    error_message = "Something went wrong. Please try again later."
                    # Log the error in production
                    print(f"Contact form error: {e}")
    
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
        'success_message': success_message,
        'error_message': error_message,
    }
    return render(request, 'website/contact.html', context)

def program_detail(request, program_id):
    """Program detail page"""
    program = get_object_or_404(Program, id=program_id)
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()
    # Get active testimonials for display
    testimonials = Testimonial.objects.filter(is_active=True).order_by('created_at')
    # Get certificates for this program (max 4)
    certificates = program.certificates.all()[:4]
    
    context = {
        'program': program,
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
        'testimonials': testimonials,
        'certificates': certificates,
    }
    return render(request, 'website/program_detail.html', context)

def program_list(request):
    """All programs listing page with filters and search"""
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get ALL programs (including both regular and advanced programs)
    all_programs = Program.objects.all()
    # Get advanced programs list for navigation
    advance_programs = Program.get_advanced_programs()
    
    # Get category filter from URL parameter
    selected_category_id = request.GET.get('category')
    selected_category = None
    
    if selected_category_id:
        try:
            selected_category = Category.objects.get(id=selected_category_id)
        except Category.DoesNotExist:
            selected_category = None
    
    # Calculate statistics from all programs
    total_programs = all_programs.count()
    regular_programs_count = all_programs.exclude(category__name='Advanced Program').count()
    advanced_programs_count = all_programs.filter(category__name='Advanced Program').count()
    bestseller_count = all_programs.filter(is_best_seller=True).count()
    
    context = {
        'programs': all_programs,
        'categories': categories,
        'total_programs': total_programs,
        'regular_programs_count': regular_programs_count,
        'advanced_programs_count': advanced_programs_count,
        'bestseller_count': bestseller_count,
        'selected_category': selected_category,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/program_list.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def submit_program_enquiry(request):
    """Handle program enquiry form submission via AJAX"""
    try:
        # Parse JSON data from request
        data = json.loads(request.body)
        
        # Extract form data
        first_name = data.get('first_name', '').strip()
        phone_number = data.get('phone_number', '').strip()
        email = data.get('email', '').strip()
        college_name = data.get('college_name', '').strip()
        program_id = data.get('program_id')
        
        # Validate required fields
        if not all([first_name, phone_number, email, college_name, program_id]):
            return JsonResponse({
                'success': False,
                'message': 'All fields are required.'
            }, status=400)
        
        # Validate email format
        from django.core.validators import validate_email
        from django.core.exceptions import ValidationError
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({
                'success': False,
                'message': 'Please enter a valid email address.'
            }, status=400)
        
        # Validate program exists
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invalid program selected.'
            }, status=400)
        
        # Check if enquiry already exists for this email and program
        existing_enquiry = ProgramEnquiry.objects.filter(
            email=email,
            program=program
        ).first()
        
        if existing_enquiry:
            # Update existing enquiry if it's older than 30 days or in closed status
            from django.utils import timezone
            days_since_enquiry = (timezone.now() - existing_enquiry.created_at).days
            
            if existing_enquiry.follow_up_status in ['closed', 'not_interested'] or days_since_enquiry > 30:
                # Update existing enquiry
                existing_enquiry.first_name = first_name
                existing_enquiry.phone_number = phone_number
                existing_enquiry.college_name = college_name
                existing_enquiry.follow_up_status = 'new'
                existing_enquiry.notes = f"Updated enquiry on {timezone.now().strftime('%Y-%m-%d %H:%M')}"
                existing_enquiry.save()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Thank you! Your enquiry has been updated. Our team will contact you soon.',
                    'enquiry_id': existing_enquiry.id
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'You have already enquired about this program. Our team will contact you soon.'
                })
        
        # Create new enquiry
        enquiry = ProgramEnquiry.objects.create(
            program=program,
            first_name=first_name,
            phone_number=phone_number,
            email=email,
            college_name=college_name,
            follow_up_status='new'
        )
        
        # Optional: Send notification email to admin (uncomment if needed)
        # try:
        #     from django.core.mail import send_mail
        #     from django.conf import settings
        #     
        #     subject = f"New Program Enquiry - {program.title}"
        #     message = f"""
        #     New enquiry received:
        #     
        #     Name: {first_name}
        #     Email: {email}
        #     Phone: {phone_number}
        #     College: {college_name}
        #     Program: {program.title} - {program.subtitle}
        #     
        #     Please follow up with the student.
        #     """
        #     
        #     send_mail(
        #         subject,
        #         message,
        #         settings.DEFAULT_FROM_EMAIL,
        #         [settings.ADMIN_EMAIL],
        #         fail_silently=True
        #     )
        # except Exception as e:
        #     # Log error but don't fail the request
        #     print(f"Failed to send notification email: {e}")
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your enquiry! Our team will contact you within 24 hours.',
            'enquiry_id': enquiry.id
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid request format.'
        }, status=400)
        
    except Exception as e:
        # Log the error for debugging
        print(f"Error in submit_program_enquiry: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing your enquiry. Please try again.'
        }, status=500)

def certificate_check(request):
    """Certificate verification page"""
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/certificate_check.html', context)

@csrf_exempt
@require_http_methods(["POST"])
def verify_certificate(request):
    """API endpoint to verify certificate"""
    try:
        data = json.loads(request.body)
        certificate_number = data.get('certificate_number', '').strip().upper()
        
        if not certificate_number:
            return JsonResponse({
                'success': False,
                'message': 'Certificate number is required'
            }, status=400)
        
        # Import UserCertificate model
        from topgrade_api.models import UserCertificate
        
        # Search for certificates with the given certificate number
        certificates = UserCertificate.objects.filter(
            certificate_number=certificate_number
            # Removing status filter to see all certificates
        ).select_related('user', 'program', 'course_progress')
        
        if certificates.exists():
            # Debug: Log the certificates found
            for cert in certificates:
                print(f"DEBUG: Certificate - Type: {cert.certificate_type}, Status: {cert.status}, Has File: {bool(cert.certificate_file)}")
            
            # Check if this is a Gold Pass user by looking at the purchase
            first_cert = certificates.first()
            is_goldpass_purchase = first_cert.course_progress.purchase.require_goldpass
            
            # Group certificates by student (since one number can have multiple certificate types)
            certificate_data = []
            student_name = None
            program_name = None
            issue_date = None
            
            # Get basic info from first certificate
            student_name = first_cert.user.fullname or first_cert.user.email
            program_name = f"{first_cert.program.title} - {first_cert.program.subtitle}"
            program_description = first_cert.program.description or f"Course in {first_cert.program.category.name}"
            program_duration = first_cert.program.duration  # Get duration from program model
            issue_date = first_cert.issued_date.strftime('%B %d, %Y')
            completion_date = first_cert.course_progress.completed_at.strftime('%B %d, %Y') if first_cert.course_progress.completed_at else 'N/A'
            
            # Determine certificate package type first
            has_placement = any(cert.certificate_type == 'placement' for cert in certificates)
            package_type = "Gold Pass Package" if has_placement else "Standard Package"
            
            # Collect all certificate types and files
            certificate_types = []
            for cert in certificates:
                cert_info = {
                    'type': cert.get_certificate_type_display(),
                    'type_code': cert.certificate_type,
                    'file_url': cert.certificate_file.url if cert.certificate_file else None,
                    'status': cert.get_status_display(),
                    'issued_date': cert.issued_date.strftime('%B %d, %Y'),
                    'has_file': bool(cert.certificate_file),
                }
                certificate_types.append(cert_info)
            
            # Debug information
            cert_types_found = [cert.certificate_type for cert in certificates]
            expected_types = ['internship', 'training', 'credit', 'recommendation']
            if has_placement:
                expected_types.append('placement')
            missing_types = [t for t in expected_types if t not in cert_types_found]
            
            
            # Check if expected certificates are missing for Gold Pass users
            if is_goldpass_purchase and len(missing_types) > 0:
                print(f"WARNING: Gold Pass user missing certificates: {missing_types}")
                
            if not is_goldpass_purchase and len(cert_types_found) != 4:
                print(f"WARNING: Standard user should have 4 certificates, but found: {len(cert_types_found)}")
                
            if is_goldpass_purchase and len(cert_types_found) != 5:
                print(f"WARNING: Gold Pass user should have 5 certificates, but found: {len(cert_types_found)}")
            
            return JsonResponse({
                'success': True,
                'certificate': {
                    'student_name': student_name,
                    'program_name': program_name,
                    'program_description': program_description,
                    'program_duration': program_duration,
                    'provider': 'TopGrade Innovation Pvt. Ltd.',
                    'issue_date': issue_date,
                    'completion_date': completion_date,
                    'certificate_number': certificate_number,
                    'package_type': package_type,
                    'certificate_count': len(certificate_types),
                    'certificates': certificate_types,
                    'debug_info': {
                        'found_types': cert_types_found,
                        'expected_types': expected_types,
                        'missing_types': missing_types,
                        'total_found': len(cert_types_found),
                        'total_expected': len(expected_types),
                    }
                }
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Certificate not found. Please check the certificate number and try again.'
            }, status=404)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)

def terms(request):
     # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/terms.html', context)

def privacy(request):
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/privacy.html', context)

def refund_policy(request):
    # Get all categories except 'Advanced Program' that have at least one program
    categories = Category.objects.exclude(name='Advanced Program').filter(programs__isnull=False).distinct()
    # Get all programs (including advanced programs)
    programs = Program.get_regular_programs()
    # Get advanced programs list
    advance_programs = Program.get_advanced_programs()

    context = {
        'categories': categories,
        'programs': programs,
        'advance_programs': advance_programs,
    }
    return render(request, 'website/refund.html', context)

def terms_app(request):
    return render(request, 'website/terms_app.html')

def privacy_app(request):
    return render(request, 'website/privacy_app.html')


def delete_account_request(request):
    """Page for users to request account deletion"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = data.get('email', '').strip()
            phone_number = data.get('phone_number', '').strip()
            reason = data.get('reason', '').strip()
            
            # Validate that at least one identifier is provided
            if not email and not phone_number:
                return JsonResponse({
                    'success': False,
                    'message': 'Please provide either an email or phone number.'
                }, status=400)
            
            # Create the deletion request
            deletion_request = DeleteAccountRequest.objects.create(
                email=email if email else None,
                phone_number=phone_number if phone_number else None,
                reason=reason if reason else None
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Your account deletion request has been submitted successfully. We will process it within 7-10 business days.'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'An error occurred: {str(e)}'
            }, status=500)
    
    # GET request - render the form page
    return render(request, 'website/delete_account_request.html')