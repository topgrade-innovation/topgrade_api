from django.http import JsonResponse
from ..schemas import AreaOfInterestSchema
from .common import api as api, AuthBearer
from django.contrib.auth import get_user_model

User = get_user_model()

@api.post("/add-area-of-interest", auth=AuthBearer())
def add_area_of_interest(request, data: AreaOfInterestSchema):
    """
    Add area of interest for authenticated user
    """
    try:
        user = request.auth
        user.area_of_intrest = data.area_of_intrest
        user.save()
        
        return {
            "success": True,
            "message": "Area of interest updated successfully",
            "area_of_intrest": user.area_of_intrest
        }
    except Exception as e:
        return JsonResponse({"message": f"Error updating area of interest: {str(e)}"}, status=500)