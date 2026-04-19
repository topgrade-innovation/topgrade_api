from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from django.utils import timezone
import json
from topgrade_api.models import Contact
from .auth_view import admin_required


@admin_required
def contact_view(request):
    """Contact submissions management view"""
    # Get filter parameters
    search_query = request.GET.get('search', '')
    date_filter = request.GET.get('date', '')
    
    # Base queryset
    contacts = Contact.objects.all().order_by('-created_at')
    
    # Apply filters
    if search_query:
        contacts = contacts.filter(
            Q(full_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(contact_no__icontains=search_query) |
            Q(subject__icontains=search_query) |
            Q(message__icontains=search_query)
        )
    
    if date_filter:
        if date_filter == 'today':
            contacts = contacts.filter(created_at__date=timezone.now().date())
        elif date_filter == 'week':
            week_ago = timezone.now() - timezone.timedelta(days=7)
            contacts = contacts.filter(created_at__gte=week_ago)
        elif date_filter == 'month':
            month_ago = timezone.now() - timezone.timedelta(days=30)
            contacts = contacts.filter(created_at__gte=month_ago)
    
    # Pagination
    paginator = Paginator(contacts, 10)  # Show 10 contacts per page
    page = request.GET.get('page')
    
    try:
        contacts_page = paginator.page(page)
    except PageNotAnInteger:
        contacts_page = paginator.page(1)
    except EmptyPage:
        contacts_page = paginator.page(paginator.num_pages)
    
    current_page = contacts_page.number
    num_pages = paginator.num_pages
    page_window = []
    for p in paginator.page_range:
        if p == 1 or p == num_pages or (current_page - 2 <= p <= current_page + 2):
            page_window.append(('page', p))
        elif p == current_page - 3 or p == current_page + 3:
            page_window.append(('ellipsis', p))

    context = {
        'user': request.user,
        'page_obj': contacts_page,
        'page_window': page_window,
        'current_filters': {
            'search': search_query,
            'date': date_filter,
        },
        'date_choices': [
            ('', 'All Time'),
            ('today', 'Today'),
            ('week', 'This Week'),
            ('month', 'This Month'),
        ],
    }
    return render(request, 'dashboard/contacts.html', context)


@admin_required
@require_POST
@csrf_exempt
def delete_contact(request):
    """Delete contact via AJAX"""
    try:
        data = json.loads(request.body)
        contact_id = data.get('contact_id')
        
        if not contact_id:
            return JsonResponse({
                'success': False,
                'message': 'Contact ID is required'
            })
        
        contact = Contact.objects.get(id=contact_id)
        contact.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Contact deleted successfully'
        })
        
    except Contact.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Contact not found'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON data'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting contact: {str(e)}'
        })