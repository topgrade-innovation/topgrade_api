from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from topgrade_api.models import Testimonial
from .auth_view import admin_required


@admin_required
def testimonials_view(request):
    """Testimonials management view"""
    testimonials = Testimonial.objects.all().order_by('-created_at')
    context = {
        'user': request.user,
        'testimonials': testimonials
    }
    return render(request, 'dashboard/testimonials.html', context)

@admin_required
def add_testimonial(request):
    """Add new testimonial"""
    if request.method == 'POST':
        name = request.POST.get('name')
        field_of_study = request.POST.get('field_of_study')
        title = request.POST.get('title')
        content = request.POST.get('content')
        avatar_image = request.FILES.get('avatar_image')
        
        if name and field_of_study and title and content:
            try:
                testimonial = Testimonial.objects.create(
                    name=name,
                    field_of_study=field_of_study,
                    title=title,
                    content=content,
                    avatar_image=avatar_image,
                    is_active=True
                )
                messages.success(request, 'Testimonial added successfully')
            except Exception as e:
                messages.error(request, f'Error adding testimonial: {str(e)}')
        else:
            messages.error(request, 'Name, field of study, title, and content are required')
    
    return redirect('dashboard:testimonials')

@admin_required
def edit_testimonial(request, testimonial_id):
    """Edit testimonial"""
    try:
        testimonial = Testimonial.objects.get(id=testimonial_id)
    except Testimonial.DoesNotExist:
        messages.error(request, 'Testimonial not found')
        return redirect('dashboard:testimonials')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        field_of_study = request.POST.get('field_of_study')
        title = request.POST.get('title')
        content = request.POST.get('content')
        avatar_image = request.FILES.get('avatar_image')
        
        if name and field_of_study and title and content:
            try:
                testimonial.name = name
                testimonial.field_of_study = field_of_study
                testimonial.title = title
                testimonial.content = content
                if avatar_image:
                    # Delete old image if it exists
                    if testimonial.avatar_image:
                        testimonial.avatar_image.delete(save=False)
                    testimonial.avatar_image = avatar_image
                testimonial.save()
                messages.success(request, 'Testimonial updated successfully')
            except Exception as e:
                messages.error(request, f'Error updating testimonial: {str(e)}')
        else:
            messages.error(request, 'Name, field of study, title, and content are required')
    
    return redirect('dashboard:testimonials')

@admin_required
def delete_testimonial(request, testimonial_id):
    """Delete testimonial"""
    try:
        testimonial = Testimonial.objects.get(id=testimonial_id)
        
        # Delete the avatar image file if it exists
        if testimonial.avatar_image:
            testimonial.avatar_image.delete(save=False)
        
        testimonial.delete()
        messages.success(request, 'Testimonial deleted successfully')
    except Testimonial.DoesNotExist:
        messages.error(request, 'Testimonial not found')
    except Exception as e:
        messages.error(request, f'Error deleting testimonial: {str(e)}')
    
    return redirect('dashboard:testimonials')

@admin_required
def toggle_testimonial_status(request, testimonial_id):
    """Toggle testimonial active status"""
    try:
        testimonial = Testimonial.objects.get(id=testimonial_id)
        testimonial.is_active = not testimonial.is_active
        testimonial.save()
        
        status = "activated" if testimonial.is_active else "deactivated"
        messages.success(request, f'Testimonial by {testimonial.name} {status} successfully')
        
    except Testimonial.DoesNotExist:
        messages.error(request, 'Testimonial not found')
    except Exception as e:
        messages.error(request, f'Error updating testimonial: {str(e)}')
    
    return redirect('dashboard:testimonials')