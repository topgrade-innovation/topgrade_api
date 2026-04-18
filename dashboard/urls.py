from django.urls import path
from . import views
from .views.video_upload_view import generate_presigned_url, confirm_upload, generate_hls_presigned_url

app_name = 'dashboard'

urlpatterns = [
    # Dashboard authentication
    path('signin/', views.signin_view, name='signin'),
    path('logout/', views.dashboard_logout, name='logout'),
    
    # Dashboard main views
    path('', views.dashboard_home, name='dashboard'),
    path('edit_category/<int:id>', views.edit_category_view, name='edit_category'),
    path('delete_category/<int:id>', views.delete_category_view, name='delete_category'),
    path('programs/', views.programs_view, name='programs'),
    path('edit_program/<int:id>', views.edit_program_view, name='edit_program'),
    path('delete_program/<int:id>', views.delete_program_view, name='delete_program'),
    path('students/', views.students_view, name='students'),
    path('student/<int:student_id>/', views.student_details_view, name='student_details'),
    path('assign-programs/', views.assign_programs_view, name='assign_programs'),
    path('student-certificates/', views.student_certificates_view, name='student_certificates'),
    path('api/generate-certificate/', views.generate_certificate_ajax, name='generate_certificate_ajax'),
    path('api/send-certificate/', views.send_certificate_ajax, name='send_certificate_ajax'),
    path('chat/', views.chat_view, name='chat'),
    path('carousel/', views.carousel_view, name='carousel'),
    path('gallery/', views.gallery_view, name='gallery'),
    path('program/<int:program_id>/', views.program_details_view, name='program_details'),
    
    # Video upload endpoints
    path('api/generate-presigned-url/', generate_presigned_url, name='generate_presigned_url'),
    path('api/confirm-upload/', confirm_upload, name='confirm_upload'),
    path('api/generate-hls-presigned-url/', generate_hls_presigned_url, name='generate_hls_presigned_url'),
    
    # Testimonials management
    path('testimonials/', views.testimonials_view, name='testimonials'),
    path('testimonials/add/', views.add_testimonial, name='add_testimonial'),
    path('testimonials/edit/<int:testimonial_id>/', views.edit_testimonial, name='edit_testimonial'),
    path('testimonials/delete/<int:testimonial_id>/', views.delete_testimonial, name='delete_testimonial'),
    path('testimonials/toggle/<int:testimonial_id>/', views.toggle_testimonial_status, name='toggle_testimonial_status'),
    
    # Certificates management
    path('certificates/', views.certificates_view, name='certificates'),
    path('certificates/add/', views.add_certificate, name='add_certificate'),
    path('certificates/edit/<int:certificate_id>/', views.edit_certificate, name='edit_certificate'),
    path('certificates/delete/<int:certificate_id>/', views.delete_certificate, name='delete_certificate'),
    
    # Program Enquiries management
    path('enquiries/', views.program_enquiries, name='program_enquiries'),
    path('api/update-enquiry-status/', views.update_enquiry_status, name='update_enquiry_status'),
    path('api/assign-enquiry/', views.assign_enquiry, name='assign_enquiry'),
    path('api/unassign-enquiry/', views.unassign_enquiry, name='unassign_enquiry'),
    path('api/unassign-program-from-student/', views.unassign_program_from_student, name='unassign_program_from_student'),
    path('api/delete-enquiry/', views.delete_enquiry, name='delete_enquiry'),
    path('api/assign-program-from-enquiry/', views.assign_program_from_enquiry, name='assign_program_from_enquiry'),
    path('api/assign-programs-bulk/', views.assign_programs_bulk, name='assign_programs_bulk'),

    # Contact management
    path('contact/', views.contact_view, name='contact'),
    path('api/delete-contact/', views.delete_contact, name='delete_contact'),
    
    # Notification management
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/', views.notification_details, name='notification_details'),
    path('api/send-notification/', views.send_notification, name='send_notification'),
    path('api/delete-notification/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('api/send-test-notification/', views.send_test_notification, name='send_test_notification'),
    path('api/get-program-students/<int:program_id>/', views.get_program_students, name='get_program_students'),
    path('fcm-tokens/', views.fcm_tokens_view, name='fcm_tokens'),
]   