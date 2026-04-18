"""
Program-related API views
"""
from django.http import JsonResponse
from ..models import Program, Category, UserPurchase, UserBookmark, UserCourseProgress, UserTopicProgress, Topic, ProgramEnquiry
from django.db import models
from .common import api, AuthBearer
import random

@api.get("/landing", auth=AuthBearer())
def get_landing_data(request):
    """
    Get landing page data with different program groups
    Returns: top_course, recently_added, featured, programs, advanced_programs
    Each group contains max 5 programs
    """
    try:
        def format_program_data(program, user):
            """Helper function to format program data consistently"""
            discounted_price = program.discounted_price  # Use the property from unified model
            
            # Count enrolled students for this program
            enrolled_students = UserPurchase.objects.filter(
                program=program,
                status='completed'
            ).count()
            
            # Check if user has bookmarked this program
            is_bookmarked = UserBookmark.objects.filter(
                user=user,
                program=program
            ).exists() if user else False
            
            return {
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
                    "discounted_price": float(discounted_price),
                    "savings": float(program.price - discounted_price)
                },
            }
        
        # Get authenticated user
        user = request.auth
        
        # Top Courses - Highest rated programs (both regular and advanced)
        top_course_programs = list(Program.objects.filter(
            program_rating__gte=4.0
        ).order_by('-program_rating', '-id')[:10])  # Get 10 to shuffle from
        
        # Shuffle and take 5
        random.shuffle(top_course_programs)
        top_course = []
        for program in top_course_programs[:5]:
            top_course.append(format_program_data(program, user))
        
        # Recently Added - Latest programs by created_at/ID
        recently_added_programs = Program.objects.all().order_by('-created_at', '-id')[:5]
        
        recently_added = []
        for program in recently_added_programs:
            recently_added.append(format_program_data(program, user))
        
        # Featured - Best seller programs
        featured_programs = list(Program.objects.filter(
            is_best_seller=True
        ).order_by('-program_rating', '-id')[:10])  # Get 10 to shuffle from
        
        # Shuffle and take 5
        random.shuffle(featured_programs)
        featured = []
        for program in featured_programs[:5]:
            featured.append(format_program_data(program, user))
        
        # Programs - Regular programs only (not Advanced Program category)
        regular_programs = list(Program.get_regular_programs().order_by('-program_rating', '-id')[:10])  # Get 10 to shuffle from
        
        # Shuffle and take 5
        random.shuffle(regular_programs)
        programs = []
        for program in regular_programs[:5]:
            programs.append(format_program_data(program, user))
        
        # Advanced Programs - Advanced programs only (Advanced Program category)
        advance_programs = Program.get_advanced_programs().order_by('-program_rating', '-id')[:5]
        advanced_programs = []
        for program in advance_programs:
            advanced_programs.append(format_program_data(program, user))
        
        # Continue Watching - Recently watched programs for authenticated users only
        continue_watching = []
        
        if user:
            # Get user's recent topic progress (videos they've started but not completed)
            recent_progress = UserTopicProgress.objects.filter(
                user=user,
                status__in=['in_progress', 'completed']
            ).select_related(
                'purchase__program',
                'topic__syllabus__program'
            ).order_by('-last_watched_at')[:10]  # Get more to filter unique programs
            
            seen_programs = set()
            for progress in recent_progress:
                if len(continue_watching) >= 5:
                    break
                    
                # Get the program from the progress
                program = progress.purchase.program
                
                if program and program.id not in seen_programs:
                    seen_programs.add(program.id)
                    
                    # Get course progress for this program
                    course_progress = UserCourseProgress.objects.filter(
                        user=user,
                        purchase=progress.purchase
                    ).first()
                    
                    program_data = format_program_data(program, user)
                    
                    # Add progress information
                    program_data['progress'] = {
                        "percentage": float(course_progress.completion_percentage) if course_progress else 0.0,
                        "status": "completed" if course_progress and course_progress.is_completed else "in_progress",
                        "last_watched_at": progress.last_watched_at.isoformat(),
                        "last_watched_topic": progress.topic.topic_title if progress.topic else "Unknown Topic",
                        "completed_topics": course_progress.completed_topics if course_progress else 0,
                        "total_topics": course_progress.total_topics if course_progress else 0
                    }
                    
                    continue_watching.append(program_data)
        
        return {
            "success": True,
            "data": {
                "top_course": top_course[:5],  # Ensure max 5
                "recently_added": recently_added[:5],  # Ensure max 5
                "featured": featured[:5],  # Ensure max 5
                "programs": programs,  # Already limited to 5
                "advanced_programs": advanced_programs,  # Already limited to 5
                "continue_watching": continue_watching  # Max 5, empty if not authenticated
            },
            "counts": {
                "top_course": len(top_course[:5]),
                "recently_added": len(recently_added[:5]),
                "featured": len(featured[:5]),
                "programs": len(programs),
                "advanced_programs": len(advanced_programs),
                "continue_watching": len(continue_watching)
            }
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching landing data: {str(e)}"}, status=500)

@api.get("/programs/filter", auth=AuthBearer())
def get_all_programs_with_filters(
    request,
    category_id: int = None,
    is_best_seller: bool = None,
    min_price: float = None,
    max_price: float = None,
    min_rating: float = None,
    search: str = None,
    sort_by: str = 'most_relevant',
    sort_order: str = 'asc'
):
    """
    Get all programs with comprehensive filtering options
    Uses unified Program model with category-based filtering
    """
    try:
        # Get authenticated user
        user = request.auth
        
        # Start with all programs
        programs_query = Program.objects.all().select_related('category')
        
        # Apply category filter
        if category_id is not None:
            try:
                category = Category.objects.get(id=category_id)
                programs_query = programs_query.filter(category=category)
            except Category.DoesNotExist:
                pass  # Skip invalid category
        
        # Apply other filters
        if is_best_seller is not None:
            programs_query = programs_query.filter(is_best_seller=is_best_seller)
        
        if min_price is not None:
            programs_query = programs_query.filter(price__gte=min_price)
        
        if max_price is not None:
            programs_query = programs_query.filter(price__lte=max_price)
        
        if min_rating is not None:
            programs_query = programs_query.filter(program_rating__gte=min_rating)
        
        if search:
            programs_query = programs_query.filter(
                models.Q(title__icontains=search) | 
                models.Q(description__icontains=search) |
                models.Q(subtitle__icontains=search)
            )
        
        # Apply sorting
        if sort_by == 'most_relevant':
            # Sort by relevance: best sellers first, then by rating
            programs_query = programs_query.order_by('-is_best_seller', '-program_rating', '-id')
        elif sort_by == 'recently_added':
            # Sort by creation date (newest first)
            programs_query = programs_query.order_by('-created_at', '-id')
        elif sort_by == 'top_rated':
            # Sort by rating (highest first)
            programs_query = programs_query.order_by('-program_rating', '-id')
        elif sort_by == 'title':
            order_field = 'title' if sort_order == 'asc' else '-title'
            programs_query = programs_query.order_by(order_field)
        elif sort_by == 'price':
            order_field = 'price' if sort_order == 'asc' else '-price'
            programs_query = programs_query.order_by(order_field)
        elif sort_by == 'program_rating':
            order_field = 'program_rating' if sort_order == 'asc' else '-program_rating'
            programs_query = programs_query.order_by(order_field)
        else:
            # Default sorting
            programs_query = programs_query.order_by('-program_rating', '-id')
        
        # Convert to list and format response
        all_programs = []
        for program in programs_query:
            # Check if user has bookmarked this program
            is_bookmarked = UserBookmark.objects.filter(
                user=user,
                program=program
            ).exists() if user else False
            
            # Count enrolled students
            enrolled_students = UserPurchase.objects.filter(
                program=program,
                status='completed'
            ).count()
            
            program_data = {
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
            }
            all_programs.append(program_data)
        
        # Get filter statistics
        total_count = len(all_programs)
        regular_count = sum(1 for p in all_programs if p['category'] and p['category']['name'] != 'Advanced Program')
        advanced_count = sum(1 for p in all_programs if p['category'] and p['category']['name'] == 'Advanced Program')
        
        return {
            "success": True,
            "filters_applied": {
                "category_id": category_id,
                "is_best_seller": is_best_seller,
                "min_price": min_price,
                "max_price": max_price,
                "min_rating": min_rating,
                "search": search,
                "sort_by": sort_by,
                "sort_order": sort_order
            },
            "statistics": {
                "total_count": total_count,
                "regular_programs_count": regular_count,
                "advanced_programs_count": advanced_count
            },
            "programs": all_programs
        }
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching filtered programs: {str(e)}"}, status=500)

@api.get("/program/{program_id}/details", auth=AuthBearer())
def get_program_details(request, program_id: int):
    """
    Get detailed information about a specific program including syllabus and topics
    Uses unified Program model - automatically handles both regular and advanced programs
    """
    try:
        # Get program from unified model
        try:
            program = Program.objects.select_related('category').prefetch_related(
                'syllabuses__topics'
            ).get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({
                "success": False, 
                "message": "Program not found"
            }, status=404)
        
        # Check if user has purchased this program (for video access)
        user = request.auth
        has_purchased = False
        purchase_id = None
        is_bookmarked = False
        has_program_requested = False
        
        if user:
            purchase = UserPurchase.objects.filter(
                user=user,
                program=program,
                status='completed'
            ).first()
            
            if purchase:
                has_purchased = True
                purchase_id = purchase.id
            
            # Check if user has bookmarked this program
            is_bookmarked = UserBookmark.objects.filter(
                user=user,
                program=program
            ).exists()
            
            # Check if user has requested/enquired about this program
            has_program_requested = ProgramEnquiry.objects.filter(
                email=user.email,
                program=program
            ).exists()
        
        # Get syllabus with topics
        syllabus_list = []
        syllabi = program.syllabuses.all().order_by('order', 'id')
        
        for syllabus in syllabi:
            topics_list = []
            topics = syllabus.topics.all().order_by('order', 'id')
            
            for topic in topics:
                # Determine video access: intro videos or free trial always accessible, others only if purchased
                video_url = ""
                is_accessible = False
                
                if (topic.is_intro or topic.is_free_trial) and topic.video_file:
                    # Intro videos and free trial videos are always accessible
                    video_url = topic.video_file.url
                    is_accessible = True
                elif has_purchased and topic.video_file:
                    # All videos accessible if user purchased
                    video_url = topic.video_file.url
                    is_accessible = True
                # Otherwise, video_url remains empty string
                
                topic_data = {
                    "id": topic.id,
                    "topic_title": topic.topic_title,
                    "description": topic.description,
                    "video_url": video_url,
                    "video_duration": topic.video_duration,
                    "is_intro": topic.is_intro,
                    "is_free_trial": topic.is_free_trial,
                    "is_accessible": is_accessible
                }
                
                topics_list.append(topic_data)
            
            syllabus_data = {
                "id": syllabus.id,
                "module_title": syllabus.module_title,
                "topics_count": len(topics_list),
                "topics": topics_list
            }
            syllabus_list.append(syllabus_data)
        
        # Count enrolled students
        enrolled_students = UserPurchase.objects.filter(
            program=program,
            status='completed'
        ).count()
        
        # Build program data
        program_data = {
            "id": program.id,
            "title": program.title,
            "subtitle": program.subtitle,
            "category": {
                "id": program.category.id,
                "name": program.category.name,
            } if program.category else None,
            "description": program.description,
            "image": program.image.url if program.image else None,
            "icon": program.icon,
            "duration": program.duration,
            "batch_starts": program.batch_starts,
            "available_slots": program.available_slots,
            "job_openings": program.job_openings,
            "global_market_size": program.global_market_size,
            "avg_annual_salary": program.avg_annual_salary,
            "program_rating": float(program.program_rating),
            "is_best_seller": program.is_best_seller,
            "is_bookmarked": is_bookmarked,
            "has_purchased": has_purchased,
            "has_program_requested": has_program_requested,
            "purchase_id": purchase_id,
            "enrolled_students": enrolled_students,
            "skills": program.skills if program.skills else [],
            "pricing": {
                "original_price": float(program.price),
                "discount_percentage": float(program.discount_percentage),
                "discounted_price": float(program.discounted_price),
                "savings": float(program.price - program.discounted_price)
            },
        }
        
        return {
            "success": True,
            "program": program_data,
            "syllabus": {
                "total_modules": len(syllabus_list),
                "total_topics": sum(len(s["topics"]) for s in syllabus_list),
                "modules": syllabus_list
            }
        }
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching program details: {str(e)}"}, status=500)