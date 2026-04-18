"""
Celery tasks for dashboard operations
"""
from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from topgrade_api.models import UserCertificate, UserCourseProgress, OTPVerification
import logging
import random

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_certificates_email_task(self, course_progress_id):
    """
    Send certificates via email as attachments.
    This task runs in the background using Celery.
    """
    try:
        # Get course progress
        course_progress = UserCourseProgress.objects.get(id=course_progress_id, is_completed=True)
        
        # Get all certificates for this course progress
        certificates = UserCertificate.objects.filter(
            user=course_progress.user,
            course_progress=course_progress,
            program=course_progress.purchase.program,
        )
        
        if not certificates.exists():
            logger.error(f"No certificates found for course progress ID: {course_progress_id}")
            return {
                'success': False,
                'message': 'No certificates found'
            }
        
        # Prepare email
        student_name = course_progress.user.fullname or course_progress.user.email
        student_email = course_progress.user.email
        program_title = course_progress.purchase.program.title
        program_subtitle = course_progress.purchase.program.subtitle
        program_full_name = f"{program_title} - {program_subtitle}"
        
        subject = f"Certificates of Completion - {program_full_name} - TopGrade Innovation"
        
        message = f"""Dear {student_name},

Congratulations on successfully completing the "{program_full_name}" program with TopGrade Innovation Pvt. Ltd. 
We appreciate your dedication and commitment throughout the training or internship period.

Your Certificates of Completion are attached to this email. Every certificate issued by TopGrade Innovation 
includes a unique verification ID.

To confirm the authenticity of your certificate, please visit our official verification portal:
    🔗 https://www.topgradeinnovation.com/certificate-verification/

You may enter the verification ID shown on your certificate to validate its authenticity.

**IMPORTANT NOTICE**

This is an automated message sent from noreply@topgradeinnovations.com
Please do not reply to this email.

For any assistance or queries, kindly contact our support team:
    📧  Email : support@topgradeinnovations.com
    📞  Phone : +91 76194 68135  |  +91 89044 65305

Thank you for being a part of TopGrade Innovation.
We wish you continued success in your future endeavors.

Best regards,
TopGrade Innovation Pvt. Ltd.
"""
        
        # Create email
        # Use EMAIL_HOST_USER as from_email to avoid SPF/DMARC issues
        email = EmailMessage(
            subject=subject,
            body=message,
            from_email=settings.EMAIL_HOST_USER,
            to=[student_email],
        )
        
        # Attach all certificates
        attached_count = 0
        for certificate in certificates:
            if certificate.certificate_file:
                try:
                    # Get the file content
                    certificate.certificate_file.open('rb')
                    file_content = certificate.certificate_file.read()
                    certificate.certificate_file.close()
                    
                    # Get filename
                    filename = f"{certificate.get_certificate_type_display()}_{certificate.certificate_number}.pdf"
                    
                    # Attach to email
                    email.attach(filename, file_content, 'application/pdf')
                    attached_count += 1
                except Exception as e:
                    logger.error(f"Error attaching certificate {certificate.id}: {str(e)}")
        
        if attached_count == 0:
            logger.error(f"No certificate files could be attached for course progress ID: {course_progress_id}")
            return {
                'success': False,
                'message': 'No certificate files available to attach'
            }
        
        # Send email
        email.send(fail_silently=False)
        
        logger.info(f"Successfully sent {attached_count} certificates to {student_email}")
        
        return {
            'success': True,
            'message': f'Successfully sent {attached_count} certificates to {student_name}',
            'email': student_email,
            'certificates_count': attached_count
        }
        
    except UserCourseProgress.DoesNotExist:
        logger.error(f"Course progress not found: {course_progress_id}")
        return {
            'success': False,
            'message': 'Course progress not found'
        }
    except Exception as e:
        logger.error(f"Error sending certificates email: {str(e)}")
        # Retry the task
        raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds


@shared_task(bind=True, max_retries=3)
def send_otp_email_task(self, email, otp_code, otp_type='signup', full_name='User'):
    """
    Send OTP via email for signup or password reset.
    This task runs in the background using Celery.
    
    Args:
        email: User's email address
        otp_code: 6-digit OTP code
        otp_type: Type of OTP - 'signup' or 'password_reset'
        full_name: User's full name (optional)
    """
    try:
        # Prepare email subject and title based on OTP type
        if otp_type == 'signup':
            subject = "Email Verification - OTP for TopGrade Innovation Signup"
            title = "Email Verification"
        else:
            subject = "Password Reset - OTP for TopGrade Innovation"
            title = "Password Reset Verification"
        
        # HTML Email Template
        html_message = f"""<!DOCTYPE html>
        <html lang="en">
        
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>OTP Verification</title>
            <style>
                * {{
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }}
        
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
                    background-color: #F4F5F7;
                    color: #172B4D;
                    line-height: 1.6;
                    padding: 20px;
                }}
        
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #ffffff;
                    border-radius: 8px;
                    overflow: hidden;
                }}
        
                .header {{
                    border-bottom: 1px solid #E5E7EB;
                    padding: 24px;
                    text-align: center;
                }}
        
                .logo-container {{
                    display: inline-flex;
                    justify-content: center;
                    align-items: center;
                    gap: 8px;
                }}
        
                .brand-name {{ 
                    font-weight: 600;
                    font-size: 18px;
                    display: block;
                    margin-left: 8px;
                }}
        
                .content {{
                    padding: 16px;
                }}
        
                .title {{
                    font-size: 18px;
                    font-weight: 600;
                    text-align: center;
                    margin: 16px 0;
                }}
        
                .greeting {{
                    font-size: 14px;
                    margin: 8px 0;
                    font-weight: 600;
                }}
        
                .text {{
                    font-size: 14px;
                    margin: 8px 0;
                }}
        
                .otp-box {{
                    margin: 16px 0;
                    border: 1px solid #E5E7EB;
                    padding: 16px;
                    border-radius: 8px;
                    text-align: center;
                }}
        
                .otp-label {{
                    font-weight: 600;
                    margin-bottom: 8px;
                }}
        
                .otp-code {{
                    font-size: 24px;
                    font-weight: 600;
                    color: #ed7d05;
                    letter-spacing: 0.1em;
                    margin: 8px 0;
                }}
        
                .otp-expiry {{
                    font-size: 12px;
                    color: #666;
                }}
        
                .security-section {{
                    margin: 16px 0;
                }}
        
                .security-title {{
                    font-weight: 600;
                    font-size: 14px;
                    margin-bottom: 8px;
                }}
        
                .instructions-list {{
                    list-style-type: disc;
                    margin: 8px 0;
                    padding-left: 32px;
                }}
        
                .instructions-list li {{
                    font-size: 14px;
                    margin: 4px 0;
                }}
        
                .signature {{
                    font-size: 14px;
                    margin: 8px 0;
                }}
        
                .footer {{
                    padding: 16px;
                    border-top: 1px solid #E5E7EB;
                    text-align: center;
                }}
        
                .footer-text {{
                    font-size: 14px;
                    color: #666;
                    margin: 0 0 8px 0;
                    display: block;
                }}
        
                .footer-brand {{
                    font-weight: 600;
                    font-size: 14px;
                    color: #6B7280;
                    margin: 0;
                    display: block;
                }}
            </style>
        </head>
        
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo-container">
                        <img src="https://raw.githubusercontent.com/dhineshio/icons/main/logo.png" alt="Creator Scribe Logo"
                            class="logo">
                        <p class="brand-name">Topgrade Innovation</p>
                    </div>
                </div>
        
                <div class="content">
                    <h1 class="title">{title}</h1>
                    <p class="greeting">Hi {full_name},</p>
                    <p class="text">
                        You recently requested an OTP. This code can be used to access your account and perform authenticated
                        operations, and as such should be kept secret.
                    </p>
                    <div class="otp-box">
                        <div class="otp-label">Your OTP Code</div>
                        <div class="otp-code">{otp_code}</div>
                        <div class="otp-expiry">This code will expire in 10 minutes</div>
                    </div>
        
                    <div class="security-section">
                        <p class="security-title">Did not request this change?</p>
                        <p class="text">
                            If you did not request this action you should immediately:
                        </p>
                        <ol class="instructions-list">
                            <li>Visit your security settings and revoke the OTP.</li>
                            <li>Change your Topgrade Innovation account password.</li>
                        </ol>
                    </div>
        
                    <p class="signature">
                        Cheers,<br>
                        The Topgrade Innovation Team
                    </p>
                </div>
                <div class="footer">
                    <p class="footer-text">This message was sent to you by Topgrade Innovation</p>
                    <p class="footer-brand">Topgrade Innovation</p>
                </div>
            </div>
        </body>
        
        </html>"""
        
        # Plain text fallback
        plain_message = f"""
Hi {full_name},

You recently requested an OTP. This code can be used to access your account and perform authenticated operations, and as such should be kept secret.

Your OTP Code: {otp_code}

This code will expire in 10 minutes.

Did not request this change?
If you did not request this action you should immediately:
1. Visit your security settings and revoke the OTP.
2. Change your Topgrade Innovation account password.

Cheers,
The Topgrade Innovation Team

---
This message was sent to you by Topgrade Innovation
"""
        
        # Create email with HTML content
        from django.core.mail import EmailMultiAlternatives
        
        email_message = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.EMAIL_HOST_USER,
            to=[email],
        )
        
        # Attach HTML version
        email_message.attach_alternative(html_message, "text/html")
        
        # Send email
        email_message.send(fail_silently=False)
        
        logger.info(f"Successfully sent OTP email to {email}")
        
        return {
            'success': True,
            'message': f'OTP email sent successfully to {email}',
            'email': email
        }
        
    except Exception as e:
        logger.error(f"Error sending OTP email to {email}: {str(e)}")
        # Retry the task
        raise self.retry(exc=e, countdown=30)  # Retry after 30 seconds


def generate_otp():
    """
    Generate a random 6-digit OTP code
    """
    return str(random.randint(100000, 999999))


@shared_task(bind=True, max_retries=3)
def calculate_video_duration_task(self, topic_id):
    """
    Calculate video duration for a topic in the background.
    This is useful for S3 videos that take time to download and process.
    
    Args:
        topic_id: ID of the Topic to calculate duration for
    
    Returns:
        dict with success status and duration
    """
    from topgrade_api.models import Topic
    from dashboard.views.program_view import calculate_video_duration_from_s3
    
    try:
        # Get the topic
        topic = Topic.objects.get(id=topic_id)
        
        if not topic.video_file:
            logger.warning(f"Topic {topic_id} has no video file")
            return {
                'success': False,
                'message': 'No video file found for this topic'
            }
        
        # Check if duration already exists
        if topic.video_duration:
            logger.info(f"Topic {topic_id} already has duration: {topic.video_duration}")
            return {
                'success': True,
                'message': 'Duration already calculated',
                'duration': topic.video_duration
            }
        
        # Calculate duration from S3
        video_file_path = str(topic.video_file)
        logger.info(f"Calculating duration for topic {topic_id}, video: {video_file_path}")
        
        duration = calculate_video_duration_from_s3(video_file_path)
        
        if duration:
            # Update the topic
            topic.video_duration = duration
            topic.save(update_fields=['video_duration'])
            
            logger.info(f"Successfully calculated and saved duration for topic {topic_id}: {duration}")
            
            return {
                'success': True,
                'message': f'Duration calculated successfully: {duration}',
                'topic_id': topic_id,
                'duration': duration
            }
        else:
            logger.error(f"Failed to calculate duration for topic {topic_id}")
            return {
                'success': False,
                'message': 'Could not calculate video duration'
            }
        
    except Topic.DoesNotExist:
        logger.error(f"Topic not found: {topic_id}")
        return {
            'success': False,
            'message': 'Topic not found'
        }
    except Exception as e:
        logger.error(f"Error calculating video duration for topic {topic_id}: {str(e)}")
        # Retry the task
        raise self.retry(exc=e, countdown=120)  # Retry after 2 minutes


@shared_task
def calculate_video_durations_bulk(topic_ids):
    """
    Calculate video durations for multiple topics in bulk.
    Useful for processing existing videos that don't have durations.
    
    Args:
        topic_ids: List of Topic IDs to process
    
    Returns:
        dict with results summary
    """
    from topgrade_api.models import Topic
    
    results = {
        'total': len(topic_ids),
        'success': 0,
        'failed': 0,
        'skipped': 0,
        'details': []
    }
    
    for topic_id in topic_ids:
        try:
            # Queue individual task for each topic
            result = calculate_video_duration_task.delay(topic_id)
            results['details'].append({
                'topic_id': topic_id,
                'task_id': result.id,
                'status': 'queued'
            })
            results['success'] += 1
        except Exception as e:
            logger.error(f"Error queuing duration calculation for topic {topic_id}: {str(e)}")
            results['failed'] += 1
            results['details'].append({
                'topic_id': topic_id,
                'status': 'failed',
                'error': str(e)
            })
    
    logger.info(f"Bulk duration calculation queued: {results['success']} tasks, {results['failed']} failed")
    
    return results
