"""
Learning progress and course tracking API views
"""
from django.http import JsonResponse
from django.utils import timezone
from django.db import models
from ..schemas import UpdateProgressSchema
from ..models import Program, UserPurchase, UserBookmark, UserCourseProgress, UserTopicProgress, Topic
from .common import api, AuthBearer

@api.get("/my-learnings", auth=AuthBearer())
def get_my_learnings(
    request,
    status: str = None  # 'onprogress', 'completed', or None for all
):
    """
    Get user's purchased courses (my learnings) with optional status filter
    Uses unified Program model with real progress tracking
    """
    try:
        user = request.auth
        
        # Get all completed purchases for the user with related data
        purchases = UserPurchase.objects.filter(
            user=user,
            status='completed'
        ).select_related('program__category').prefetch_related(
            'program__syllabuses__topics'
        ).order_by('-purchase_date')
        
        learnings_data = []
        for purchase in purchases:
            if purchase.program:
                program = purchase.program
                
                # Get actual course progress
                course_progress = UserCourseProgress.objects.filter(
                    user=user,
                    purchase=purchase
                ).first()
                
                # Calculate progress metrics
                if course_progress:
                    progress_percentage = course_progress.completion_percentage
                    completed_modules = course_progress.completed_topics
                    total_modules = course_progress.total_topics
                    is_completed = course_progress.is_completed
                    last_activity = course_progress.last_activity_at
                    
                else:
                    # Fallback for purchases without progress tracking
                    progress_percentage = 0.0
                    completed_modules = 0
                    total_modules = Topic.objects.filter(syllabus__program=program).count()
                    is_completed = False
                    last_activity = purchase.purchase_date
                
                # Apply status filter
                if status:
                    if status == 'completed' and not is_completed:
                        continue
                    elif status == 'onprogress' and is_completed:
                        continue
                
                # Check if user has bookmarked this program
                is_bookmarked = UserBookmark.objects.filter(
                    user=user,
                    program=program
                ).exists()
                
                # Count enrolled students
                enrolled_students = UserPurchase.objects.filter(
                    program=program,
                    status='completed'
                ).count()
                
                learning_data = {
                    "purchase_id": purchase.id,
                    "program": {
                        "id": program.id,
                        "title": program.title,
                        "subtitle": program.subtitle,
                        "description": program.description,
                        "category": {
                            "id": program.category.id,
                            "name": program.category.name,
                        } if program.category else None,
                        "image": program.image.url if program.image else None,
                        "duration": program.duration,
                        "program_rating": float(program.program_rating),
                        "is_best_seller": program.is_best_seller,
                        "is_bookmarked": is_bookmarked,
                        "enrolled_students": enrolled_students,
                        "pricing": {
                            "original_price": float(program.price),
                            "discount_percentage": float(program.discount_percentage),
                            "discounted_price": float(program.discounted_price),
                            "savings": float(program.price - program.discounted_price)
                        },
                    },
                    "purchase_date": purchase.purchase_date.isoformat(),
                    "amount_paid": float(purchase.amount_paid),
                    "progress": {
                        "percentage": round(float(progress_percentage), 2),
                        "status": "completed" if is_completed else "onprogress",
                        "completed_topics": completed_modules,
                        "total_topics": total_modules,
                        "completed_modules": program.syllabuses.count() if is_completed else int((progress_percentage / 100) * program.syllabuses.count()),
                        "total_modules": program.syllabuses.count(),
                        "last_activity_at": last_activity.isoformat() if last_activity else None
                    }
                }
                learnings_data.append(learning_data)
        
        # Get statistics
        total_courses = len(learnings_data)
        completed_courses = len([l for l in learnings_data if l['progress']['status'] == 'completed'])
        in_progress_courses = total_courses - completed_courses
        
        # Calculate overall progress statistics
        total_watch_time = 0
        total_possible_topics = 0
        total_completed_topics = 0
        
        for learning in learnings_data:
            total_possible_topics += learning['progress']['total_topics']
            total_completed_topics += learning['progress']['completed_topics']
        
        overall_completion_rate = round((total_completed_topics / total_possible_topics * 100), 2) if total_possible_topics > 0 else 0
        
        return {
            "success": True,
            "statistics": {
                "total_courses": total_courses,
                "completed_courses": completed_courses,
                "in_progress_courses": in_progress_courses,
                "completion_rate": round((completed_courses / total_courses * 100), 2) if total_courses > 0 else 0,
                "overall_topic_completion": overall_completion_rate,
                "total_topics_completed": total_completed_topics,
                "total_topics_available": total_possible_topics
            },
            "filter_applied": status or "all",
            "learnings": learnings_data
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching learnings: {str(e)}"}, status=500)

@api.post("/learning/update-progress", auth=AuthBearer())
def update_learning_progress(request, data: UpdateProgressSchema):
    """
    Update user's progress for a specific topic/video
    Uses unified Program model for optimized performance
    """
    try:
        user = request.auth
        
        # Validate input
        if data.watch_time_seconds < 0:
            return JsonResponse({
                "success": False,
                "message": "Invalid watch time value"
            }, status=400)
        
        # Get and validate purchase
        try:
            purchase = UserPurchase.objects.select_related('program').get(
                id=data.purchase_id,
                user=user,
                status='completed'
            )
        except UserPurchase.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Purchase not found or access denied"
            }, status=404)
        
        # Get and validate topic
        try:
            topic = Topic.objects.select_related('syllabus__program').get(id=data.topic_id)
            
            # Verify topic belongs to the purchased program
            if topic.syllabus.program != purchase.program:
                return JsonResponse({
                    "success": False,
                    "message": "Topic does not belong to the purchased program"
                }, status=400)
                
        except Topic.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Topic not found"
            }, status=404)
        
        # Parse video duration from database
        video_duration = None
        if topic.video_duration:
            try:
                duration_parts = topic.video_duration.split(':')
                if len(duration_parts) == 2:  # MM:SS
                    video_duration = int(duration_parts[0]) * 60 + int(duration_parts[1])
                elif len(duration_parts) == 3:  # HH:MM:SS
                    video_duration = int(duration_parts[0]) * 3600 + int(duration_parts[1]) * 60 + int(duration_parts[2])
            except (ValueError, IndexError):
                video_duration = None
        
        total_duration = video_duration or 1800  # Default to 30 minutes if no duration found
        
        # Get or create topic progress
        topic_progress, created = UserTopicProgress.objects.get_or_create(
            user=user,
            purchase=purchase,
            topic=topic,
            defaults={
                'status': 'not_started',
                'total_duration_seconds': total_duration,
                'watch_time_seconds': 0,
                'completion_percentage': 0.0,
                'last_watched_at': timezone.now(),
                'created_at': timezone.now()
            }
        )
        
        # Update progress with validation
        topic_progress.watch_time_seconds = max(topic_progress.watch_time_seconds, data.watch_time_seconds)
        topic_progress.total_duration_seconds = total_duration
        topic_progress.last_watched_at = timezone.now()
        
        # Calculate completion percentage
        completion_percentage = min(100.0, (topic_progress.watch_time_seconds / total_duration) * 100)
        topic_progress.completion_percentage = completion_percentage
        
        # Update status based on completion
        if completion_percentage >= 90:  # Consider 90% as completed
            topic_progress.status = 'completed'
            if not hasattr(topic_progress, 'completed_at') or not topic_progress.completed_at:
                topic_progress.completed_at = timezone.now()
        elif completion_percentage > 0:
            topic_progress.status = 'in_progress'
        
        topic_progress.save()
        
        # Update course progress efficiently
        course_progress, _ = UserCourseProgress.objects.get_or_create(
            user=user,
            purchase=purchase,
            defaults={
                'completion_percentage': 0.0,
                'completed_topics': 0,
                'in_progress_topics': 0,
                'total_topics': 0,
                'is_completed': False,
                'total_watch_time_seconds': 0,
                'last_activity_at': timezone.now()
            }
        )
        
        # Calculate course progress based on all topics in the program
        total_topics = Topic.objects.filter(syllabus__program=purchase.program).count()
        completed_topics = UserTopicProgress.objects.filter(
            user=user,
            topic__syllabus__program=purchase.program,
            status='completed'
        ).count()
        in_progress_topics = UserTopicProgress.objects.filter(
            user=user,
            topic__syllabus__program=purchase.program,
            status='in_progress'
        ).count()
        
        # Calculate total watch time for this course
        total_watch_time = UserTopicProgress.objects.filter(
            user=user,
            topic__syllabus__program=purchase.program
        ).aggregate(
            total_time=models.Sum('watch_time_seconds')
        )['total_time'] or 0
        
        # Calculate weighted progress based on actual topic completion percentages
        if total_topics > 0:
            # Get all topic progress for this program
            topic_progress_data = UserTopicProgress.objects.filter(
                user=user,
                topic__syllabus__program=purchase.program
            ).aggregate(
                total_completion=models.Sum('completion_percentage')
            )
            
            total_completion_percentage = topic_progress_data['total_completion'] or 0
            # Calculate average completion across all topics
            course_completion = total_completion_percentage / total_topics
        else:
            course_completion = 0
        
        course_progress.completion_percentage = course_completion
        course_progress.completed_topics = completed_topics
        course_progress.in_progress_topics = in_progress_topics
        course_progress.total_topics = total_topics
        course_progress.is_completed = course_completion >= 100
        course_progress.total_watch_time_seconds = total_watch_time
        course_progress.last_activity_at = timezone.now()
        course_progress.save()
        
        return {
            "success": True,
            "message": "Progress updated successfully!",
            "topic_progress": {
                "topic_id": topic.id,
                "topic_title": topic.topic_title,
                "status": topic_progress.status,
                "completion_percentage": round(float(topic_progress.completion_percentage), 2),
                "watch_time_seconds": topic_progress.watch_time_seconds,
                "total_duration_seconds": topic_progress.total_duration_seconds,
                "is_completed": topic_progress.status == 'completed',
                "last_watched_at": topic_progress.last_watched_at.isoformat()
            },
            "course_progress": {
                "completion_percentage": round(float(course_progress.completion_percentage), 2),
                "completed_topics": course_progress.completed_topics,
                "in_progress_topics": course_progress.in_progress_topics,
                "total_topics": course_progress.total_topics,
                "is_completed": course_progress.is_completed,
                "total_watch_time_seconds": course_progress.total_watch_time_seconds
            }
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error updating progress: {str(e)}"}, status=500)