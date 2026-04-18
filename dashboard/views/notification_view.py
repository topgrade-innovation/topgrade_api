from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.utils import timezone
from topgrade_api.models import Notification, NotificationLog, FCMToken, Program, CustomUser
from topgrade_api.utils.firebase_helper import send_notification_to_users, send_notification_to_user
from .auth_view import admin_required
import json

User = get_user_model()

@admin_required
def notifications_view(request):
    """
    View to manage and send notifications to students
    """
    # Get all notifications ordered by creation date
    notifications = Notification.objects.all().select_related('created_by', 'program').prefetch_related('recipients')
    
    # Get only students who have registered FCM tokens (active tokens)
    students_with_tokens = FCMToken.objects.filter(
        is_active=True
    ).values_list('user_id', flat=True).distinct()
    
    students = CustomUser.objects.filter(
        role='student',
        id__in=students_with_tokens
    ).order_by('fullname', 'email')
    
    # Get all programs for filtering/selection
    programs = Program.objects.all().order_by('title')
    
    # Get statistics
    total_notifications = notifications.count()
    sent_notifications = notifications.filter(status='sent').count()
    pending_notifications = notifications.filter(status='pending').count()
    failed_notifications = notifications.filter(status='failed').count()
    
    # Get recent notifications
    recent_notifications = notifications[:10]
    
    # Get total active FCM tokens
    total_active_tokens = FCMToken.objects.filter(is_active=True).count()
    students_with_tokens = FCMToken.objects.filter(is_active=True).values('user').distinct().count()
    
    context = {
        'user': request.user,
        'notifications': recent_notifications,
        'all_notifications': notifications,
        'students': students,
        'programs': programs,
        'total_notifications': total_notifications,
        'sent_notifications': sent_notifications,
        'pending_notifications': pending_notifications,
        'failed_notifications': failed_notifications,
        'total_active_tokens': total_active_tokens,
        'students_with_tokens': students_with_tokens,
    }
    
    return render(request, 'dashboard/notifications.html', context)

@admin_required
@require_POST
def send_notification(request):
    """
    Send notification to selected students via AJAX
    """
    try:
        # Get form data
        title = request.POST.get('title', '').strip()
        message = request.POST.get('message', '').strip()
        notification_type = request.POST.get('notification_type', 'general')
        program_id = request.POST.get('program_id')
        recipient_type = request.POST.get('recipient_type', 'all')
        selected_students = request.POST.getlist('selected_students[]')
        
        # Handle image upload
        image_url = None
        notification_image = request.FILES.get('notification_image')
        
        if notification_image:
            # Save image to media folder
            from django.core.files.storage import default_storage
            from django.core.files.base import ContentFile
            import os
            from datetime import datetime
            
            # Generate unique filename
            ext = os.path.splitext(notification_image.name)[1]
            filename = f"notifications/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{notification_image.name}"
            
            # Save file
            path = default_storage.save(filename, ContentFile(notification_image.read()))
            
            # Get full URL
            image_url = request.build_absolute_uri(default_storage.url(path))
            print(f"Image uploaded: {image_url}")
        
        # Debug logging
        print(f"=== Send Notification Debug ===")
        print(f"Title: {title}")
        print(f"Message: {message}")
        print(f"Recipient Type: {recipient_type}")
        print(f"Notification Type: {notification_type}")
        print(f"Image URL: {image_url}")
        
        # Validation
        if not title or not message:
            return JsonResponse({
                'success': False,
                'message': 'Title and message are required'
            })
        
        # Get only students with active FCM tokens
        students_with_tokens = FCMToken.objects.filter(
            is_active=True
        ).values_list('user_id', flat=True).distinct()
        
        print(f"Students with FCM tokens: {len(students_with_tokens)}")
        
        # Get recipients based on selection (only those with FCM tokens)
        if recipient_type == 'all':
            recipients = CustomUser.objects.filter(
                role='student',
                id__in=students_with_tokens
            )
        elif recipient_type == 'selected' and selected_students:
            recipients = CustomUser.objects.filter(
                role='student',
                id__in=selected_students
            ).filter(id__in=students_with_tokens)
        elif recipient_type == 'program' and program_id:
            # Students enrolled in specific program who have FCM tokens
            from topgrade_api.models import UserPurchase
            recipients = CustomUser.objects.filter(
                purchases__program_id=program_id,
                purchases__status='completed',
                role='student'
            ).filter(id__in=students_with_tokens).distinct()
        else:
            return JsonResponse({
                'success': False,
                'message': 'Please select recipients'
            })
        
        print(f"Recipients found: {recipients.count()}")
        
        if not recipients.exists():
            return JsonResponse({
                'success': False,
                'message': f'No recipients found. FCM tokens: {len(students_with_tokens)}'
            })
        
        # Get program if specified
        program = None
        if program_id:
            try:
                program = Program.objects.get(id=program_id)
            except Program.DoesNotExist:
                pass
        
        # Prepare additional data
        data = {
            'notification_type': notification_type,
        }
        if program:
            data['program_id'] = str(program.id)
            data['program_title'] = program.title
        
        print(f"Sending notification to {recipients.count()} users...")
        
        # Send notification
        notification = send_notification_to_users(
            users=list(recipients),
            title=title,
            message=message,
            notification_type=notification_type,
            data=data,
            image_url=image_url if image_url else None,
            created_by=request.user,
            program=program
        )
        
        print(f"Notification sent! Success: {notification.sent_count}, Failed: {notification.failed_count}")
        
        return JsonResponse({
            'success': True,
            'message': f'Notification sent to {notification.sent_count} student(s)',
            'notification_id': notification.id,
            'sent_count': notification.sent_count,
            'failed_count': notification.failed_count
        })
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error sending notification: {error_trace}")
        return JsonResponse({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@admin_required
def notification_details(request, notification_id):
    """
    View notification details and delivery logs
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        
        # Get delivery logs
        logs = NotificationLog.objects.filter(notification=notification).select_related('user', 'fcm_token')
        
        # Get statistics
        total_logs = logs.count()
        success_logs = logs.filter(status='success').count()
        failed_logs = logs.filter(status='failed').count()
        read_logs = logs.filter(is_read=True).count()
        
        context = {
            'user': request.user,
            'notification': notification,
            'logs': logs,
            'total_logs': total_logs,
            'success_logs': success_logs,
            'failed_logs': failed_logs,
            'read_logs': read_logs,
        }
        
        return render(request, 'dashboard/notification_details.html', context)
        
    except Notification.DoesNotExist:
        messages.error(request, 'Notification not found')
        return redirect('dashboard:notifications')

@admin_required
@require_POST
def delete_notification(request, notification_id):
    """
    Delete a notification
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        notification.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Notification deleted successfully'
        })
        
    except Notification.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Notification not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error deleting notification: {str(e)}'
        })

@admin_required
def fcm_tokens_view(request):
    """
    View and manage FCM tokens
    """
    tokens = FCMToken.objects.all().select_related('user').order_by('-created_at')
    
    # Get statistics
    total_tokens = tokens.count()
    active_tokens = tokens.filter(is_active=True).count()
    inactive_tokens = tokens.filter(is_active=False).count()
    
    # Group by device type
    android_tokens = tokens.filter(device_type='android').count()
    ios_tokens = tokens.filter(device_type='ios').count()
    web_tokens = tokens.filter(device_type='web').count()
    
    context = {
        'user': request.user,
        'tokens': tokens,
        'total_tokens': total_tokens,
        'active_tokens': active_tokens,
        'inactive_tokens': inactive_tokens,
        'android_tokens': android_tokens,
        'ios_tokens': ios_tokens,
        'web_tokens': web_tokens,
    }
    
    return render(request, 'dashboard/fcm_tokens.html', context)

@admin_required
@require_POST
def send_test_notification(request):
    """
    Send a test notification to a specific user
    """
    try:
        user_id = request.POST.get('user_id')
        title = request.POST.get('title', 'Test Notification')
        message = request.POST.get('message', 'This is a test notification')
        
        if not user_id:
            return JsonResponse({
                'success': False,
                'message': 'User ID is required'
            })
        
        user = CustomUser.objects.get(id=user_id)
        
        success, result_message = send_notification_to_user(
            user=user,
            title=title,
            message=message,
            notification_type='system'
        )
        
        return JsonResponse({
            'success': success,
            'message': result_message
        })
        
    except CustomUser.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'User not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error sending test notification: {str(e)}'
        })

@admin_required
def get_program_students(request, program_id):
    """
    Get list of students enrolled in a specific program who have FCM tokens (AJAX)
    """
    try:
        from topgrade_api.models import UserPurchase
        
        # Get only students with active FCM tokens
        students_with_tokens = FCMToken.objects.filter(
            is_active=True
        ).values_list('user_id', flat=True).distinct()
        
        students = CustomUser.objects.filter(
            purchases__program_id=program_id,
            purchases__status='completed',
            role='student',
            id__in=students_with_tokens
        ).distinct().values('id', 'fullname', 'email')
        
        return JsonResponse({
            'success': True,
            'students': list(students),
            'count': len(students)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })
