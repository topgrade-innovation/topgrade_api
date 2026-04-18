"""
Custom storage backends for AWS S3 integration
"""
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage


class MediaStorage(S3Boto3Storage):
    """Custom S3 storage backend for media files"""
    location = 'media'
    default_acl = None  # Changed from 'public-read' to None (ACLs disabled)
    file_overwrite = False
    querystring_auth = False
    object_parameters = {
        'CacheControl': 'max-age=86400',
    }
    
    # Use CloudFront domain if configured, otherwise use S3 domain
    @property
    def custom_domain(self):
        if hasattr(settings, 'USE_CLOUDFRONT') and settings.USE_CLOUDFRONT:
            if hasattr(settings, 'AWS_CLOUDFRONT_DOMAIN') and settings.AWS_CLOUDFRONT_DOMAIN:
                return settings.AWS_CLOUDFRONT_DOMAIN
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
            return settings.AWS_S3_CUSTOM_DOMAIN
        return None


class StaticStorage(S3Boto3Storage):
    """Custom S3 storage backend for static files"""
    location = 'static'
    default_acl = None  # Changed from 'public-read' to None (ACLs disabled)
    file_overwrite = True  # Static files can be overwritten
    querystring_auth = False
    object_parameters = {
        'CacheControl': 'max-age=86400',
    }
    
    # Use CloudFront domain if configured, otherwise use S3 domain
    @property
    def custom_domain(self):
        if hasattr(settings, 'USE_CLOUDFRONT') and settings.USE_CLOUDFRONT:
            if hasattr(settings, 'AWS_CLOUDFRONT_DOMAIN') and settings.AWS_CLOUDFRONT_DOMAIN:
                return settings.AWS_CLOUDFRONT_DOMAIN
        if hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
            return settings.AWS_S3_CUSTOM_DOMAIN
        return None