from .auth_view import admin_required
from django.shortcuts import render, redirect
from django.contrib import messages
from topgrade_api.models import Carousel
from django.core.files.storage import default_storage
import os

@admin_required
def carousel_view(request):
    """Carousel view for dashboard"""
    
    # Handle POST requests for carousel management
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'upload':
            # Handle image upload
            image_file = request.FILES.get('image')
            if image_file:
                try:
                    # Create new carousel slide
                    carousel_slide = Carousel.objects.create(
                        image=image_file,
                        is_active=True
                    )
                    messages.success(request, 'Image uploaded successfully!')
                except Exception as e:
                    messages.error(request, f'Error uploading image: {str(e)}')
            else:
                messages.error(request, 'Please select an image to upload.')
        
        elif action == 'toggle_active':
            # Handle toggle active/inactive
            slide_id = request.POST.get('slide_id')
            if slide_id:
                try:
                    slide = Carousel.objects.get(id=slide_id)
                    slide.is_active = not slide.is_active
                    slide.save()
                    status = 'activated' if slide.is_active else 'deactivated'
                    messages.success(request, f'Image {status} successfully!')
                except Carousel.DoesNotExist:
                    messages.error(request, 'Image not found.')
                except Exception as e:
                    messages.error(request, f'Error updating image: {str(e)}')
        
        elif action == 'delete':
            # Handle image deletion
            slide_id = request.POST.get('slide_id')
            if slide_id:
                try:
                    slide = Carousel.objects.get(id=slide_id)
                    # Delete the image file
                    if slide.image and default_storage.exists(slide.image.name):
                        default_storage.delete(slide.image.name)
                    # Delete the slide record
                    slide.delete()
                    messages.success(request, 'Image deleted successfully!')
                except Carousel.DoesNotExist:
                    messages.error(request, 'Image not found.')
                except Exception as e:
                    messages.error(request, f'Error deleting image: {str(e)}')
        
        return redirect('dashboard:carousel')
    
    # Get carousel data for display
    carousel_slides = Carousel.objects.all().order_by('order', '-created_at')
    
    # Calculate statistics
    total_slides = carousel_slides.count()
    active_slides = carousel_slides.filter(is_active=True).count()
    inactive_slides = total_slides - active_slides
    
    context = {
        'user': request.user,
        'carousel_slides': carousel_slides,
        'total_slides': total_slides,
        'active_slides': active_slides,
        'inactive_slides': inactive_slides,
    }
    return render(request, 'dashboard/carousel.html', context)