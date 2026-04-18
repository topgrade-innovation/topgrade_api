"""
Management command to calculate/recalculate durations for HLS topics (master.m3u8)
"""
from django.core.management.base import BaseCommand
from topgrade_api.models import Topic
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate durations for topics whose video is an HLS master.m3u8'

    def add_arguments(self, parser):
        parser.add_argument(
            '--topic-id',
            type=int,
            help='Process a specific topic ID only',
        )
        parser.add_argument(
            '--program-id',
            type=int,
            help='Process all HLS topics in a specific program',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Recalculate even topics that already have a duration stored',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List matched topics without calculating anything',
        )

    def handle(self, *args, **options):
        topic_id  = options.get('topic_id')
        program_id = options.get('program_id')
        recalculate_all = options.get('all')
        dry_run   = options.get('dry_run')

        from dashboard.views.program_view import calculate_hls_duration_from_s3

        # --- build base queryset: only topics with an .m3u8 video ---
        qs = Topic.objects.filter(video_file__endswith='master.m3u8')

        if topic_id:
            qs = qs.filter(id=topic_id)
        elif program_id:
            qs = qs.filter(syllabus__program_id=program_id)

        if not recalculate_all:
            # Only topics that are missing a duration
            qs = qs.filter(video_duration__isnull=True) | qs.filter(video_duration='')

        qs = qs.select_related('syllabus__program')
        total = qs.count()

        if total == 0:
            self.stdout.write(self.style.SUCCESS(
                'No HLS topics found that need duration calculation.'
            ))
            return

        self.stdout.write(self.style.WARNING(f'Found {total} HLS topic(s) to process'))

        if dry_run:
            self.stdout.write(self.style.NOTICE('\n=== DRY RUN ==='))
            for topic in qs:
                video_path = str(topic.video_file)
                self.stdout.write(
                    f'  • ID {topic.id:>5} | duration={topic.video_duration or "—":>10} | '
                    f'program="{topic.syllabus.program.title}" | {video_path}'
                )
            return

        success_count = 0
        failed_count  = 0

        for idx, topic in enumerate(qs, 1):
            video_path = str(topic.video_file)
            self.stdout.write(
                f'\n[{idx}/{total}] Topic ID {topic.id} — {topic.topic_title}'
            )
            self.stdout.write(f'  Program : {topic.syllabus.program.title}')
            self.stdout.write(f'  Path    : {video_path}')

            try:
                duration = calculate_hls_duration_from_s3(video_path)

                if duration:
                    topic.video_duration = duration
                    topic.save(update_fields=['video_duration'])
                    self.stdout.write(self.style.SUCCESS(f'  Duration: {duration}'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR('  Could not calculate duration'))
                    failed_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error: {e}'))
                logger.exception(f'calculate_hls_durations failed for topic {topic.id}')
                failed_count += 1

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(f'Total : {total}')
        self.stdout.write(self.style.SUCCESS(f'OK    : {success_count}'))
        if failed_count:
            self.stdout.write(self.style.ERROR(f'Failed: {failed_count}'))
