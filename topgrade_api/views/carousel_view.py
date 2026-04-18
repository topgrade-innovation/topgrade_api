"""
Carousel and website content API views
"""
from topgrade_api.models import Carousel
from .common import api
from django.http import JsonResponse

# Carousel API Endpoints
@api.get("/carousel")
def get_carousel_slides(request):
    """
    Get all active carousel slides ordered by their position
    """
    try:
        carousel_slides = Carousel.objects.filter(is_active=True).order_by('order', 'created_at')
        
        slides_data = []
        for slide in carousel_slides:
            slide_data = {
                "id": slide.id,
                "image": slide.image.url if slide.image else None,
            }
            slides_data.append(slide_data)
        
        return {
            "success": True,
            "data": slides_data,
            "total_slides": len(slides_data)
        }
        
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "message": f"Error fetching carousel slides: {str(e)}"
        }, status=500)