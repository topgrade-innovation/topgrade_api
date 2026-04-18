"""
Management command to calculate missing video durations for existing topics
"""
from django.core.management.base import BaseCommand
from topgrade_api.models import Topic
from dashboard.tasks import calculate_video_duration_task
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate video durations for topics that are missing duration information'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topic-id',
            type=int,
            help='Calculate duration for a specific topic ID',
        )
        parser.add_argument(
            '--program-id',
            type=int,
            help='Calculate durations for all topics in a specific program',
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Run calculations asynchronously using Celery (recommended for many videos)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show topics that need duration calculation without actually calculating',
        )

    def handle(self, *args, **options):
        topic_id = options.get('topic_id')
        program_id = options.get('program_id')
        use_async = options.get('async')
        dry_run = options.get('dry_run')

        # Build query
        if topic_id:
            topics = Topic.objects.filter(id=topic_id)
        elif program_id:
            topics = Topic.objects.filter(
                syllabus__program_id=program_id,
                video_file__isnull=False
            ).exclude(video_file='')
        else:
            # Get all topics with videos but no duration
            topics = Topic.objects.filter(
                video_file__isnull=False
            ).exclude(video_file='')

        # Filter topics without duration
        topics_without_duration = topics.filter(
            video_duration__isnull=True
        ) | topics.filter(video_duration='')

        total_count = topics_without_duration.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✓ All topics with videos already have duration calculated!'))
            return

        self.stdout.write(self.style.WARNING(f'Found {total_count} topics without video duration'))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n=== DRY RUN - Topics that need duration calculation ==='))
            for topic in topics_without_duration:
                self.stdout.write(
                    f'  • Topic ID: {topic.id} | Program: {topic.syllabus.program.title} | '
                    f'Video: {topic.video_file.name if hasattr(topic.video_file, "name") else topic.video_file}'
                )
            return

        # Process topics
        self.stdout.write(self.style.NOTICE(f'\nProcessing {total_count} topics...'))
        
        success_count = 0
        failed_count = 0
        
        for idx, topic in enumerate(topics_without_duration, 1):
            self.stdout.write(f'\n[{idx}/{total_count}] Processing Topic ID: {topic.id}')
            self.stdout.write(f'  Program: {topic.syllabus.program.title}')
            self.stdout.write(f'  Topic: {topic.topic_title}')
            
            try:
                if use_async:
                    # Queue Celery task
                    task = calculate_video_duration_task.delay(topic.id)
                    self.stdout.write(self.style.NOTICE(f'  ⏳ Queued for background processing (Task ID: {task.id})'))
                    success_count += 1
                else:
                    # Calculate synchronously
                    from dashboard.views.program_view import calculate_video_duration_from_s3
                    
                    video_file_path = str(topic.video_file)
                    self.stdout.write(f'  Video path: {video_file_path}')
                    
                    duration = calculate_video_duration_from_s3(video_file_path)
                    
                    if duration:
                        topic.video_duration = duration
                        topic.save(update_fields=['video_duration'])
                        self.stdout.write(self.style.SUCCESS(f'  ✓ Duration calculated: {duration}'))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(f'  ✗ Failed to calculate duration'))
                        failed_count += 1
                        
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Error: {str(e)}'))
                failed_count += 1
        
        # Summary
        self.stdout.write(self.style.NOTICE('\n' + '='*60))
        self.stdout.write(self.style.NOTICE('SUMMARY'))
        self.stdout.write(self.style.NOTICE('='*60))
        self.stdout.write(f'Total topics processed: {total_count}')
        self.stdout.write(self.style.SUCCESS(f'✓ Successful: {success_count}'))
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f'✗ Failed: {failed_count}'))
        
        if use_async:
            self.stdout.write(self.style.WARNING('\n⚠ Tasks are running in background. Check Celery logs for progress.'))
