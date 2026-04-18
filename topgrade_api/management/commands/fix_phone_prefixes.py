"""
Management command to add +91 prefix to phone numbers that are missing it
Usage: python manage.py fix_phone_prefixes
"""

from django.core.management.base import BaseCommand
from topgrade_api.models import CustomUser
from django.db.models import Q


class Command(BaseCommand):
    help = 'Add +91 prefix to phone numbers that are missing it'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(self.style.WARNING('=' * 70))
        self.stdout.write(self.style.WARNING('Fix Phone Number Prefixes'))
        self.stdout.write(self.style.WARNING('=' * 70))
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))
        
        # Find users with phone numbers that don't start with +
        users_without_prefix = CustomUser.objects.filter(
            Q(phone_number__isnull=False) & 
            ~Q(phone_number='') & 
            ~Q(phone_number__startswith='+')
        )
        
        total_users = users_without_prefix.count()
        
        if total_users == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All users already have +91 prefix on their phone numbers!'))
            return
        
        self.stdout.write(self.style.WARNING(f'\nFound {total_users} users with phone numbers missing +91 prefix:\n'))
        
        # Display users
        for idx, user in enumerate(users_without_prefix, 1):
            self.stdout.write(f"  {idx}. {user.email} - {user.phone_number} → +91{user.phone_number}")
        
        if not dry_run:
            self.stdout.write(self.style.WARNING('\n⚠️  This will add +91 prefix to these phone numbers.'))
            confirm = input('\nDo you want to continue? (yes/no): ')
            
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('\n❌ Operation cancelled.'))
                return
        
        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('Processing users...\n')
        
        updated_count = 0
        skipped_count = 0
        
        for user in users_without_prefix:
            old_phone = user.phone_number
            new_phone = f"+91{old_phone}"
            
            if dry_run:
                self.stdout.write(
                    f"  [DRY RUN] Would update {user.email}: {old_phone} → {new_phone}"
                )
                updated_count += 1
            else:
                try:
                    # Check if the new phone number already exists (conflict)
                    if CustomUser.objects.filter(phone_number=new_phone).exclude(id=user.id).exists():
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠️  Skipped {user.email}: {new_phone} already exists for another user")
                        )
                        skipped_count += 1
                        continue
                    
                    user.phone_number = new_phone
                    user.save(update_fields=['phone_number'])
                    self.stdout.write(
                        self.style.SUCCESS(f"  ✅ Updated {user.email}: {old_phone} → {new_phone}")
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
                self.stdout.write(self.style.WARNING(f"  ⚠️  Skipped: {skipped_count} users"))
        
        self.stdout.write('=' * 70)
        
        if dry_run:
            self.stdout.write(self.style.NOTICE('\n💡 Run without --dry-run to apply changes'))
        else:
            self.stdout.write(self.style.SUCCESS('\n🎉 Operation completed successfully!'))
            self.stdout.write('\nVerify the changes:')
            self.stdout.write('  python manage.py shell')
            self.stdout.write('  >>> from topgrade_api.models import CustomUser')
            self.stdout.write('  >>> CustomUser.objects.exclude(phone_number__startswith="+").exclude(phone_number="").count()')
            self.stdout.write('  # Should return 0')
