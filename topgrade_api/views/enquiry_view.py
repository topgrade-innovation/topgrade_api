"""
Program enquiry API views for mobile app
"""
from django.http import JsonResponse
from django.utils import timezone
from ninja import Schema
from ..models import Program, ProgramEnquiry
from .common import api, AuthBearer


class ProgramEnquirySchema(Schema):
    """Schema for program enquiry request from mobile app"""
    program_id: int


@api.post("/request-program", auth=AuthBearer())
def request_program_enquiry(request, data: ProgramEnquirySchema):
    """
    Create a program enquiry from mobile app user
    
    - Authenticated endpoint (requires JWT token)
    - User details fetched from token
    - College name defaults to "mobile app"
    - Only requires program_id in request
    """
    try:
        # Get authenticated user from token
        user = request.auth
        
        # Validate program ID
        if not data.program_id:
            return JsonResponse({
                "success": False,
                "message": "program_id is required"
            }, status=400)
        
        # Get the program
        try:
            program = Program.objects.get(id=data.program_id)
        except Program.DoesNotExist:
            return JsonResponse({
                "success": False,
                "message": "Program not found"
            }, status=404)
        
        # Check if user already has an enquiry for this program
        existing_enquiry = ProgramEnquiry.objects.filter(
            email=user.email,
            program=program
        ).first()
        
        if existing_enquiry:
            # Update existing enquiry status if needed
            if existing_enquiry.follow_up_status in ['closed', 'not_interested']:
                existing_enquiry.follow_up_status = 'new'
                existing_enquiry.save()
                
                return {
                    "success": True,
                    "message": "Your enquiry has been reactivated. Our team will contact you soon.",
                    "enquiry": {
                        "id": existing_enquiry.id,
                        "program_title": program.title,
                        "program_subtitle": program.subtitle,
                        "status": existing_enquiry.get_follow_up_status_display(),
                        "created_at": existing_enquiry.created_at.isoformat(),
                    }
                }
            else:
                return JsonResponse({
                    "success": False,
                    "message": "You already have an active enquiry for this program. Our team will contact you soon."
                }, status=400)
        
        # Extract user details
        first_name = user.fullname if user.fullname else user.username
        if not first_name:
            first_name = user.email.split('@')[0]
        
        phone_number = user.phone_number if user.phone_number else "Not provided"
        email = user.email
        college_name = "mobile app"  # Default for mobile app users
        
        # Create new program enquiry
        ProgramEnquiry.objects.create(
            program=program,
            first_name=first_name,
            phone_number=phone_number,
            email=email,
            college_name=college_name,
            follow_up_status='new'
        )
        
        return {
            "success": True,
            "message": "Your enquiry has been submitted successfully! Our team will contact you soon.",
        }
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "message": f"Error submitting enquiry: {str(e)}"
        }, status=500)
