from django.apps import AppConfig
from django.db import transaction


class TopgradeApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'topgrade_api'

    def ready(self):
        """
        This method is called when Django starts.
        Create default categories automatically and initialize Firebase.
        """
        # Only run this in production/server environments, not during migrations
        import os
        import sys
        
        # Skip during migrations, testing, or management commands
        if (
            'migrate' in sys.argv or
            'makemigrations' in sys.argv or
            'test' in sys.argv or
            'collectstatic' in sys.argv or
            len(sys.argv) > 1 and sys.argv[1] in ['migrate', 'makemigrations', 'test', 'collectstatic']
        ):
            return
        
        # Create default categories
        try:
            with transaction.atomic():
                from .models import Category
                Category.create_default_categories()
        except Exception:
            # Fail silently during startup to avoid breaking the app
            # Categories can be created manually using the management command
            pass
        
        # Initialize Firebase
        try:
            from topgrade_api.firebase_config import initialize_firebase
            initialize_firebase()
        except Exception as e:
            print(f"Warning: Firebase initialization failed: {e}")
            print("Phone OTP with Firebase will not work until Firebase is properly configured.")
