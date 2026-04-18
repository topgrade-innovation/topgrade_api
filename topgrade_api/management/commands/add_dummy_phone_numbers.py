"""
Management command to add dummy phone numbers to users without phone numbers
Usage: python manage.py add_dummy_phone_numbers
"""

from django.core.management.base import BaseCommand
from topgrade_api.models import CustomUser
import random


class Command(BaseCommand):
    help = 'Add dummy phone numbers to users who do not have phone numbers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )
        parser.add_argument(
            '--prefix',
            type=str,
            default='+91999',
            help='Phone number prefix (default: +91999)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        prefix = options['prefix']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Add Dummy Phone Numbers to Existing Users'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Find users without phone numbers
        users_without_phone = CustomUser.objects.filter(
            phone_number__isnull=True
        ) | CustomUser.objects.filter(
            phone_number=''
        )
        
        total_users = users_without_phone.count()
        
        if total_users == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All users already have phone numbers!'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nFound {total_users} users without phone numbers:\n'))
        
        # Display users
        for idx, user in enumerate(users_without_phone, 1):
            self.stdout.write(f"  {idx}. {user.email} - {user.fullname or 'No name'}")
        
        if not dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  This will assign dummy phone numbers to these users.'))
            confirm = input('\nDo you want to continue? (yes/no): ')
            
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('\n❌ Operation cancelled.'))
                return
        
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('Processing users...\n')
        
        updated_count = 0
        skipped_count = 0
        
        for user in users_without_phone:
            # Generate dummy phone number
            while True:
                # Generate 7 random digits
                random_digits = ''.join([str(random.randint(0, 9)) for _ in range(7)])
                dummy_phone = f"{prefix}{random_digits}"
                
                # Check if this phone number already exists
                if not CustomUser.objects.filter(phone_number=dummy_phone).exists():
                    break
            
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would assign {dummy_phone} to {user.email}"
                )
                updated_count += 1
            else:
                try:
                    user.phone_number = dummy_phone
                    user.save(update_fields=['phone_number'])
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ Assigned {dummy_phone} to {user.email}")
                    )
                    updated_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"  ❌ Failed to update {user.email}: {str(e)}")
                    )
                    skipped_count += 1
        
        # Summary
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('Summary:'))
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(f"  Would update: {updated_count} users")
        else:
            self.stdout.write(self.style.SUCCESS(f"  ✅ Successfully updated: {updated_count} users"))
            if skipped_count > 0:
                self.stdout.write(self.style.ERROR(f"  ❌ Failed: {skipped_count} users"))
        
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n💡 Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n🎉 Operation completed successfully!'))
