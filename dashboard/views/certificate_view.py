from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from topgrade_api.models import Certificate, Program
from .auth_view import admin_required


@admin_required
def certificates_view(request):
    """Certificates management view"""
    certificates = Certificate.objects.select_related('program').order_by('-created_at')
    programs = Program.objects.all().order_by('title')
    
    context = {
        'user': request.user,
        'certificates': certificates,
        'programs': programs
    }
    return render(request, 'dashboard/certificates.html', context)

@admin_required
def add_certificate(request):
    """Add new certificate"""
    if request.method == 'POST':
        program_id = request.POST.get('program')
        certificate_image = request.FILES.get('certificate_image')
        
        if program_id and certificate_image:
            try:
                program = Program.objects.get(id=program_id)
                certificate = Certificate.objects.create(
                    program=program,
                    certificate_image=certificate_image
                )
                messages.success(request, 'Certificate added successfully')
            except Program.DoesNotExist:
                messages.error(request, 'Selected program not found')
            except Exception as e:
                messages.error(request, f'Error adding certificate: {str(e)}')
        else:
            messages.error(request, 'Program selection and certificate image are required')
    
    return redirect('dashboard:certificates')

@admin_required
def edit_certificate(request, certificate_id):
    """Edit certificate"""
    try:
        certificate = Certificate.objects.get(id=certificate_id)
    except Certificate.DoesNotExist:
        messages.error(request, 'Certificate not found')
        return redirect('dashboard:certificates')
    
    if request.method == 'POST':
        program_id = request.POST.get('program')
        certificate_image = request.FILES.get('certificate_image')
        
        if program_id:
            try:
                program = Program.objects.get(id=program_id)
                certificate.program = program
                
                # Update image if provided
                if certificate_image:
                    # Delete old image if it exists
                    if certificate.certificate_image:
                        certificate.certificate_image.delete(save=False)
                    certificate.certificate_image = certificate_image
                
                certificate.save()
                messages.success(request, 'Certificate updated successfully')
            except Program.DoesNotExist:
                messages.error(request, 'Selected program not found')
            except Exception as e:
                messages.error(request, f'Error updating certificate: {str(e)}')
        else:
            messages.error(request, 'Program selection is required')
    
    return redirect('dashboard:certificates')

@admin_required
def delete_certificate(request, certificate_id):
    """Delete certificate"""
    try:
        certificate = Certificate.objects.get(id=certificate_id)
        
        # Delete the image file if it exists
        if certificate.certificate_image:
            certificate.certificate_image.delete(save=False)
        
        certificate.delete()
        messages.success(request, 'Certificate deleted successfully')
    except Certificate.DoesNotExist:
        messages.error(request, 'Certificate not found')
    except Exception as e:
        messages.error(request, f'Error deleting certificate: {str(e)}')
    
    return redirect('dashboard:certificates')