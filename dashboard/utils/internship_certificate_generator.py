import os
from io import BytesIO
from datetime import datetime
from django.core.files.base import ContentFile
from django.conf import settings
from django.template.loader import render_to_string


def generate_certificate_pdf(user, program, certificate_number, completion_date=None, purchase_date=None, certificate_type='internship'):
    """
    Generate a PDF certificate for a student using HTML template
    
    Args:
        user: CustomUser object (student)
        program: Program object
        certificate_number: Unique certificate number
        completion_date: Date of course completion (defaults to today)
        purchase_date: Date when the program was purchased
        certificate_type: Type of certificate ('internship', 'training', 'credit', 'recommendation', 'placement')
    
    Returns:
        ContentFile object containing the PDF
    """
    # Set completion date
    if completion_date:
        completion_date_str = completion_date.strftime("%d %B %Y")
    else:
        completion_date_str = datetime.now().strftime("%d %B %Y")
    
    # Set purchase date (start date)
    if purchase_date:
        purchase_date_str = purchase_date.strftime("%d %B %Y")
    else:
        purchase_date_str = datetime.now().strftime("%d %B %Y")
    
    # Student name
    student_name = user.fullname or user.email.split('@')[0]
    
    # Program name
    program_name = f"{program.title} {program.subtitle}"
    
    # Certificate template mapping
    template_mapping = {
        'internship': 'certificates/internship_certificate_template.html',
        'training': 'certificates/training_certificate_template.html',
        'credit': 'certificates/credit_certificate_template.html',
        'recommendation': 'certificates/letter_of_recommendation_template.html',
        'placement': 'certificates/placement_certificate.html',
    }
    
    # Prepare context for template
    context = {
        'student_name': student_name,
        'program_name': program_name,
        'certificate_number': certificate_number,
        'completion_date': completion_date_str,
        'purchase_date': purchase_date_str,
    }
    
    # Get template based on certificate type
    template_path = template_mapping.get(certificate_type, 'certificates/internship_certificate_template.html')
    
    # Render HTML template
    html_string = render_to_string(template_path, context)
    
    # Import WeasyPrint only when needed (lazy loading)
    from weasyprint import HTML
    
    # Generate PDF from HTML
    html = HTML(string=html_string)
    pdf_bytes = html.write_pdf()
    
    # Create a ContentFile from the PDF data
    filename = f"{certificate_type}_certificate_{certificate_number}.pdf"
    return ContentFile(pdf_bytes, name=filename)


def generate_bulk_certificates(user, program, base_certificate_number, completion_date=None, purchase_date=None, include_placement=True):
    """
    Generate multiple certificates for a student with the same certificate number
    
    Args:
        user: CustomUser object (student)
        program: Program object
        base_certificate_number: Base certificate number (same for all certificates)
        completion_date: Date of course completion (defaults to today)
        purchase_date: Date when the program was purchased
        include_placement: Whether to include placement certificate (based on require_goldpass)
    
    Returns:
        Dictionary with certificate type as key and ContentFile as value
    """
    certificates = {}
    
    # Define certificate types
    certificate_types = ['internship', 'training', 'credit', 'recommendation']
    
    # Add placement certificate if goldpass is required
    if include_placement:
        certificate_types.append('placement')
    
    # Generate each certificate type with the same certificate number
    for cert_type in certificate_types:
        try:
            pdf_file = generate_certificate_pdf(
                user=user,
                program=program,
                certificate_number=base_certificate_number,
                completion_date=completion_date,
                purchase_date=purchase_date,
                certificate_type=cert_type
            )
            certificates[cert_type] = pdf_file
        except Exception as e:
            print(f"Error generating {cert_type} certificate: {str(e)}")
            # Continue with other certificates even if one fails
            continue
    
    return certificates
