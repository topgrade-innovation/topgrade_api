from .auth_view import admin_required
from django.shortcuts import render, redirect
from django.contrib import messages
from topgrade_api.models import Gallery
from django.core.files.storage import default_storage
import os

@admin_required
def gallery_view(request):
    """Gallery view for dashboard"""
    
    # Handle POST requests for gallery management
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'upload':
            # Handle image upload
            alt_text = request.POST.get('alt_text', '').strip()
            image_file = request.FILES.get('image')
            
            if not image_file:
                messages.error(request, 'Please select an image to upload.')
            else:
                try:
                    # Create new gallery image
                    gallery_image = Gallery.objects.create(
                        alt_text=alt_text if alt_text else None,
                        image=image_file,
                        is_active=True
                    )
                    messages.success(request, 'Image uploaded successfully!')
                except Exception as e:
                    messages.error(request, f'Error uploading image: {str(e)}')
        
        elif action == 'update':
            # Handle image update
            image_id = request.POST.get('image_id')
            alt_text = request.POST.get('alt_text', '').strip()
            
            if image_id:
                try:
                    gallery_image = Gallery.objects.get(id=image_id)
                    gallery_image.alt_text = alt_text if alt_text else None
                    gallery_image.save()
                    messages.success(request, 'Image updated successfully!')
                except Gallery.DoesNotExist:
                    messages.error(request, 'Image not found.')
                except Exception as e:
                    messages.error(request, f'Error updating image: {str(e)}')
            else:
                messages.error(request, 'Invalid image ID.')
        
        elif action == 'toggle_active':
            # Handle toggle active/inactive
            image_id = request.POST.get('image_id')
            if image_id:
                try:
                    gallery_image = Gallery.objects.get(id=image_id)
                    gallery_image.is_active = not gallery_image.is_active
                    gallery_image.save()
                    status = 'activated' if gallery_image.is_active else 'deactivated'
                    messages.success(request, f'Image {status} successfully!')
                except Gallery.DoesNotExist:
                    messages.error(request, 'Image not found.')
                except Exception as e:
                    messages.error(request, f'Error updating image: {str(e)}')
        
        elif action == 'delete':
            # Handle image deletion
            image_id = request.POST.get('image_id')
            if image_id:
                try:
                    gallery_image = Gallery.objects.get(id=image_id)
                    # Delete the image file
                    if gallery_image.image and default_storage.exists(gallery_image.image.name):
                        default_storage.delete(gallery_image.image.name)
                    # Delete the image record
                    gallery_image.delete()
                    messages.success(request, 'Image deleted successfully!')
                except Gallery.DoesNotExist:
                    messages.error(request, 'Image not found.')
                except Exception as e:
                    messages.error(request, f'Error deleting image: {str(e)}')
        
        return redirect('dashboard:gallery')
    
    # Get gallery data for display
    gallery_images = Gallery.objects.all().order_by('-created_at')
    
    # Calculate statistics
    total_images = gallery_images.count()
    active_images = gallery_images.filter(is_active=True).count()
    inactive_images = total_images - active_images
    
    context = {
        'user': request.user,
        'gallery_images': gallery_images,
        'total_images': total_images,
        'active_images': active_images,
        'inactive_images': inactive_images,
    }
    return render(request, 'dashboard/gallery.html', context)