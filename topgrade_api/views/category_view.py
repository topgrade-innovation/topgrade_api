"""
Category-related API views
"""
from django.http import JsonResponse
from ..models import Category
from .common import api, AuthBearer

@api.get("/categories", auth=AuthBearer())
def get_categories(request):
    """
    Get list of all categories
    """
    try:
        categories = Category.objects.all().order_by('name')
        
        categories_data = []
        for category in categories:
            category_data = {
                "id": category.id,
                "name": category.name,
            }
            categories_data.append(category_data)
        
        return {
            "success": True,
            "count": len(categories_data),
            "categories": categories_data
        }
    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error fetching categories: {str(e)}"}, status=500)