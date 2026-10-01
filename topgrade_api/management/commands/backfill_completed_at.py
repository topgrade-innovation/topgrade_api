"""
Management command to fill missing completed_at for completed courses
Usage: python manage.py backfill_completed_at [--dry-run]
"""

from django.core.management.base import BaseCommand
from django.db.models import Max
from topgrade_api.models import UserCourseProgress, UserTopicProgress


class Command(BaseCommand):
    help = 'Fill missing completed_at for completed courses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without actually updating',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n🔍 DRY RUN MODE - No changes will be made\n'))

        missing = UserCourseProgress.objects.filter(
            is_completed=True, completed_at__isnull=True
        ).select_related('user', 'purchase__program')

        total = missing.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS('\n✅ All completed courses already have a completed date!'))
            return

        self.stdout.write(self.style.WARNING(f'\nFound {total} completed courses without completed date:\n'))

        for idx, progress in enumerate(missing, 1):
            # Best guess: when the last topic was completed, else last activity
            last_topic_done = UserTopicProgress.objects.filter(
                user_id=progress.user_id,
                purchase_id=progress.purchase_id,
                completed_at__isnull=False,
            ).aggregate(latest=Max('completed_at'))['latest']
            completed_at = last_topic_done or progress.last_activity_at

            self.stdout.write(
                f"  {idx}. {progress.user.email} - {progress.get_program_title()} → {completed_at:%d/%m/%Y %H:%M}"
            )

            if not dry_run:
                # update() avoids bumping last_activity_at (auto_now)
                UserCourseProgress.objects.filter(pk=progress.pk).update(completed_at=completed_at)

        if dry_run:
            self.stdout.write(self.style.NOTICE(f'\n🔍 {total} courses would be updated'))
        else:
            self.stdout.write(self.style.SUCCESS(f'\n✅ Updated {total} courses'))
