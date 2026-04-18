from django.core.management.base import BaseCommand
from django.db import transaction
from topgrade_api.models import Category


class Command(BaseCommand):
    help = 'Create default categories including Advanced Program'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of categories (will update existing ones)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Creating default categories...')
        )
        
        try:
            with transaction.atomic():
                created_categories = Category.create_default_categories()
                
                if created_categories:
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'✅ Successfully created {len(created_categories)} categories:'
                        )
                    )
                    for category_name in created_categories:
                        self.stdout.write(f'   - {category_name}')
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            'ℹ️  All default categories already exist. No new categories created.'
                        )
                    )
                
                # Show all existing categories
                all_categories = Category.objects.all()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'\n📋 Total categories in database: {all_categories.count()}'
                    )
                )
                for category in all_categories:
                    self.stdout.write(f'   - {category.name}')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating categories: {str(e)}')
            )
            raise e
        
        self.stdout.write(
            self.style.SUCCESS('\n🎉 Default categories setup completed!')
        )