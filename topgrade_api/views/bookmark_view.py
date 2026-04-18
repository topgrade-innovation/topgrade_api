"""
Bookmark-related API views
"""
from django.http import JsonResponse
from django.utils import timezone
from ..schemas import BookmarkSchema
from ..models import Program, UserBookmark, UserPurchase
from .common import api, AuthBearer

@api.post("/bookmark", auth=AuthBearer())
def add_to_bookmark(request, data: BookmarkSchema):
    """
    Add a program to user's bookmarks
    Uses unified Program model - works for both regular and advanced programs
    """
    try:
        user = request.auth
        
        # Get request data from schema
        program_id = data.program_id
        
        # Get the program from unified model
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({"success": False, "message": "Program not found"}, status=404)
        
        # Check if already bookmarked
        existing_bookmark = UserBookmark.objects.filter(
            user=user,
            program=program
        ).first()
        
        if existing_bookmark:
            return JsonResponse({
                "success": False,
                "message": "Course is already in your bookmarks"
            }, status=400)
        
        # Create bookmark
        bookmark = UserBookmark.objects.create(
            user=user,
            program=program,
            bookmarked_date=timezone.now()
        )
        
        return {
            "success": True,
            "message": "Course added to bookmarks successfully!",
            "bookmark": {
                "id": bookmark.id,
                "program_title": program.title,
                "program_id": program.id,
                "bookmarked_date": bookmark.bookmarked_date.isoformat()
            }
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error adding bookmark: {str(e)}"}, status=500)

@api.delete("/bookmark", auth=AuthBearer())
def remove_from_bookmark(request, data: BookmarkSchema):
    """
    Remove a program from user's bookmarks
    Uses unified Program model
    """
    try:
        user = request.auth
        
        # Get request data from schema
        program_id = data.program_id
        
        # Get the program from unified model
        try:
            program = Program.objects.get(id=program_id)
        except Program.DoesNotExist:
            return JsonResponse({"success": False, "message": "Program not found"}, status=404)
        
        # Find and delete bookmark
        bookmark = UserBookmark.objects.filter(
            user=user,
            program=program
        ).first()
        
        if not bookmark:
            return JsonResponse({
                "success": False,
                "message": "Course is not in your bookmarks"
            }, status=404)
        
        program_title = program.title
        bookmark.delete()
        
        return {
            "success": True,
            "message": f"'{program_title}' removed from bookmarks successfully!"
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error removing bookmark: {str(e)}"}, status=500)

@api.get("/bookmarks", auth=AuthBearer())
def get_user_bookmarks(request):
    """
    Get all bookmarks for the authenticated user
    Uses unified Program model
    """
    try:
        user = request.auth
        
        # Get all user bookmarks with related program data
        bookmarks = UserBookmark.objects.filter(user=user).select_related(
            'program__category'
        ).order_by('-bookmarked_date')
        
        bookmarks_data = []
        for bookmark in bookmarks:
            if bookmark.program:
                program = bookmark.program
                
                # Count enrolled students
                enrolled_students = UserPurchase.objects.filter(
                    program=program,
                    status='completed'
                ).count()
                
                bookmark_data = {
                    "bookmark_id": bookmark.id,
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
                        "enrolled_students": enrolled_students,
                        "pricing": {
                            "original_price": float(program.price),
                            "discount_percentage": float(program.discount_percentage),
                            "discounted_price": float(program.discounted_price),
                            "savings": float(program.price - program.discounted_price)
                        },
                    },
                    "bookmarked_date": bookmark.bookmarked_date.isoformat()
                }
                bookmarks_data.append(bookmark_data)
        
        return {
            "success": True,
            "count": len(bookmarks_data),
            "bookmarks": bookmarks_data
        }
        
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching bookmarks: {str(e)}"}, status=500)