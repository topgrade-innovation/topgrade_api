from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
import json
from topgrade_api.models import ProgramEnquiry
from .auth_view import admin_required


@admin_required
def program_enquiries(request):
    """Program enquiries management view"""
    # Get filter parameters
    status_filter = request.GET.get('status', '')
    program_filter = request.GET.get('program', '')
    assigned_filter = request.GET.get('assigned', '')
    search_query = request.GET.get('search', '')
    
    # Base queryset
    enquiries = ProgramEnquiry.objects.select_related('program', 'assigned_to').all().order_by('-created_at')
    
    # Apply filters
    if status_filter:
        enquiries = enquiries.filter(follow_up_status=status_filter)
    
    if program_filter:
        enquiries = enquiries.filter(program_id=program_filter)
    
    if assigned_filter == 'unassigned':
        enquiries = enquiries.filter(assigned_to__isnull=True)
    elif assigned_filter:
        enquiries = enquiries.filter(assigned_to_id=assigned_filter)
    
    if search_query:
        enquiries = enquiries.filter(
            Q(first_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(phone_number__icontains=search_query) |
            Q(program__title__icontains=search_query)
        )
    
    # Pagination
    paginator = Paginator(enquiries, 10)  # Show 10 enquiries per page
    page = request.GET.get('page')
    
    try:
        enquiries_page = paginator.page(page)
    except PageNotAnInteger:
        enquiries_page = paginator.page(1)
    except EmptyPage:
        enquiries_page = paginator.page(paginator.num_pages)
    
    # Get counts for different statuses
    total_count = ProgramEnquiry.objects.count()
    new_count = ProgramEnquiry.objects.filter(follow_up_status='new').count()
    contacted_count = ProgramEnquiry.objects.filter(follow_up_status='contacted').count()
    interested_count = ProgramEnquiry.objects.filter(follow_up_status='interested').count()
    enrolled_count = ProgramEnquiry.objects.filter(follow_up_status='enrolled').count()
    closed_count = ProgramEnquiry.objects.filter(follow_up_status='closed').count()
    
    # Calculate needs_follow_up count
    needs_follow_up_count = sum([
        ProgramEnquiry.objects.filter(follow_up_status='new', created_at__lt=timezone.now() - timezone.timedelta(days=1)).count(),
        ProgramEnquiry.objects.filter(follow_up_status='contacted', created_at__lt=timezone.now() - timezone.timedelta(days=3)).count(),
        ProgramEnquiry.objects.filter(follow_up_status='follow_up_needed').count(),
    ])
    
    # Get all programs for filter dropdown
    from topgrade_api.models import Program
    programs = Program.objects.all()
    
    # Get all staff members for assignment dropdown
    from django.contrib.auth import get_user_model
    User = get_user_model()
    staff_members = User.objects.filter(role__in=['admin', 'operations_staff'])
    
    current_page = enquiries_page.number
    num_pages = paginator.num_pages
    page_window = []
    for p in paginator.page_range:
        if p == 1 or p == num_pages or (current_page - 2 <= p <= current_page + 2):
            page_window.append(('page', p))
        elif p == current_page - 3 or p == current_page + 3:
            page_window.append(('ellipsis', p))

    context = {
        'user': request.user,
        'page_obj': enquiries_page,  # Template expects 'page_obj'
        'stats': {  # Template expects 'stats' object
            'total': total_count,
            'new': new_count,
            'needs_follow_up': needs_follow_up_count,
            'enrolled': enrolled_count,
        },
        'current_filters': {  # Template expects 'current_filters' object
            'search': search_query,
            'status': status_filter,
            'program': program_filter,
            'assigned': assigned_filter,
        },
        'programs': programs,
        'staff_members': staff_members,
        'status_choices': ProgramEnquiry.FOLLOW_UP_STATUS_CHOICES,
        'page_window': page_window,
    }
    return render(request, 'dashboard/program_enquiries.html', context)

@admin_required
@require_POST
@csrf_exempt
def update_enquiry_status(request):
    """Update enquiry status via AJAX"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        new_status = data.get('status')
        
        if not enquiry_id or not new_status:
            return JsonResponse({
                'success': False,
                'message': 'Enquiry ID and status are required'
            })
        
        enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
        enquiry.follow_up_status = new_status
        enquiry.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Status updated to {new_status.title()}'
        })
        
    except ProgramEnquiry.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enquiry not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error updating status: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def assign_enquiry(request):
    """Assign enquiry to staff member via AJAX"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        staff_id = data.get('staff_id')
        
        if not enquiry_id:
            return JsonResponse({
                'success': False,
                'message': 'Enquiry ID is required'
            })
        
        enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
        
        if staff_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                staff_member = User.objects.get(id=staff_id)
                enquiry.assigned_to = staff_member
                message = f'Enquiry assigned to {staff_member.email}'
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Staff member not found'
                })
        else:
            enquiry.assigned_to = None
            message = 'Assignment removed'
        
        enquiry.save()
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except ProgramEnquiry.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enquiry not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning enquiry: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def assign_program_from_enquiry(request):
    """Assign program to student from enquiry"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        email = data.get('email')
        program_id = data.get('program_id')
        require_goldpass = data.get('require_goldpass', False)
        
        if not email or not program_id:
            return JsonResponse({
                'success': False,
                'message': 'Email and Program ID are required'
            })
        
        from django.contrib.auth import get_user_model
        from topgrade_api.models import Program, UserPurchase
        
        User = get_user_model()
        
        # Get or create user
        user, created = User.objects.get_or_create(
            email=email,
            defaults={'role': 'student'}
        )
        
        # Get program
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Program not found'
            })
        
        # Check if already assigned
        existing_purchase = UserPurchase.objects.filter(
            user=user,
            program=program
        ).first()
        
        if existing_purchase:
            return JsonResponse({
                'success': False,
                'message': f'Program already assigned to {email}'
            })
        
        # Create purchase/assignment
        UserPurchase.objects.create(
            user=user,
            program=program,
            status='completed',
            amount_paid=program.discounted_price,
            require_goldpass=require_goldpass
        )
        
        # Update enquiry status if enquiry_id provided
        if enquiry_id:
            try:
                enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
                enquiry.follow_up_status = 'enrolled'
                enquiry.save()
            except ProgramEnquiry.DoesNotExist:
                pass
        
        return JsonResponse({
            'success': True,
            'message': f'Program "{program.title}" assigned to {email} successfully' + 
                      (' (Gold Pass required)' if require_goldpass else '')
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning program: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def assign_programs_bulk(request):
    """Assign programs to multiple students in bulk"""
    try:
        data = json.loads(request.body)
        assignments = data.get('assignments', [])
        require_goldpass = data.get('require_goldpass', False)
        
        if not assignments:
            return JsonResponse({
                'success': False,
                'message': 'No assignments provided'
            })
        
        from django.contrib.auth import get_user_model
        from topgrade_api.models import Program, UserPurchase
        from django.db import transaction
        
        User = get_user_model()
        
        success_count = 0
        error_count = 0
        errors = []
        
        with transaction.atomic():
            for assignment in assignments:
                email = assignment.get('email')
                program_id = assignment.get('program_id')
                enquiry_id = assignment.get('enquiry_id')
                
                if not email or not program_id:
                    error_count += 1
                    errors.append(f'Missing email or program_id')
                    continue
                
                try:
                    # Get or create user
                    user, created = User.objects.get_or_create(
                        email=email,
                        defaults={'role': 'student'}
                    )
                    
                    # Get program
                    program = Program.objects.get(id=program_id)
                    
                    # Check if already assigned
                    existing_purchase = UserPurchase.objects.filter(
                        user=user,
                        program=program
                    ).first()
                    
                    if existing_purchase:
                        error_count += 1
                        errors.append(f'{email}: Already assigned')
                        continue
                    
                    # Create purchase/assignment
                    UserPurchase.objects.create(
                        user=user,
                        program=program,
                        status='completed',
                        amount_paid=program.discounted_price,
                        require_goldpass=require_goldpass
                    )
                    
                    # Update enquiry status
                    if enquiry_id:
                        try:
                            enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
                            enquiry.follow_up_status = 'enrolled'
                            enquiry.save()
                        except ProgramEnquiry.DoesNotExist:
                            pass
                    
                    success_count += 1
                    
                except Program.DoesNotExist:
                    error_count += 1
                    errors.append(f'{email}: Program not found')
                except Exception as e:
                    error_count += 1
                    errors.append(f'{email}: {str(e)}')
        
        message = f'Successfully assigned {success_count} program(s)'
        if error_count > 0:
            message += f', {error_count} failed'
        if require_goldpass:
            message += ' (Gold Pass required)'
        
        return JsonResponse({
            'success': True if success_count > 0 else False,
            'message': message,
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error assigning programs: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def unassign_enquiry(request):
    """Unassign staff member from enquiry via AJAX"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        
        if not enquiry_id:
            return JsonResponse({
                'success': False,
                'message': 'Enquiry ID is required'
            })
        
        enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
        enquiry.assigned_to = None
        enquiry.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Enquiry unassigned successfully'
        })
        
    except ProgramEnquiry.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enquiry not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error unassigning enquiry: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def unassign_program_from_student(request):
    """Unassign/remove program from student via AJAX"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        
        if not enquiry_id:
            return JsonResponse({
                'success': False,
                'message': 'Enquiry ID is required'
            })
        
        enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
        
        # Find and delete the UserPurchase record
        from django.contrib.auth import get_user_model
        from topgrade_api.models import UserPurchase
        
        User = get_user_model()
        
        try:
            user = User.objects.get(email=enquiry.email)
            purchase = UserPurchase.objects.filter(
                user=user,
                program=enquiry.program
            ).first()
            
            if purchase:
                purchase.delete()
                
                # Update enquiry status back to interested
                enquiry.follow_up_status = 'interested'
                enquiry.save()
                
                return JsonResponse({
                    'success': True,
                    'message': f'Program "{enquiry.program.title}" unassigned from {enquiry.email} successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'No program assignment found for this student'
                })
                
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Student not found'
            })
        
    except ProgramEnquiry.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enquiry not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error unassigning program: {str(e)}'
        })


@admin_required
@require_POST
@csrf_exempt
def delete_enquiry(request):
    """Delete enquiry via AJAX - also unassigns program if assigned"""
    try:
        data = json.loads(request.body)
        enquiry_id = data.get('enquiry_id')
        
        if not enquiry_id:
            return JsonResponse({
                'success': False,
                'message': 'Enquiry ID is required'
            })
        
        enquiry = ProgramEnquiry.objects.get(id=enquiry_id)
        
        # If enquiry is in enrolled status, unassign the program first
        if enquiry.follow_up_status == 'enrolled':
            from django.contrib.auth import get_user_model
            from topgrade_api.models import UserPurchase
            
            User = get_user_model()
            
            try:
                user = User.objects.get(email=enquiry.email)
                purchase = UserPurchase.objects.filter(
                    user=user,
                    program=enquiry.program
                ).first()
                
                if purchase:
                    purchase.delete()
            except User.DoesNotExist:
                pass  # User doesn't exist, continue with deletion
        
        # Delete the enquiry
        enquiry.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Enquiry deleted successfully (program unassigned if it was assigned)'
        })
        
    except ProgramEnquiry.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Enquiry not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting enquiry: {str(e)}'
        })