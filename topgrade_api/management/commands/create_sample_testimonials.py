from django.core.management.base import BaseCommand
from topgrade_api.models import Testimonial


class Command(BaseCommand):
    help = 'Create sample testimonials for testing and demonstration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing testimonials before creating new ones',
        )

    def handle(self, *args, **options):
        if options['clear']:
            Testimonial.objects.all().delete()
            self.stdout.write(
                self.style.WARNING('Cleared all existing testimonials')
            )

        # Sample testimonials data
        testimonials_data = [
            {
                'name': 'Ashi Dabhade',
                'field_of_study': 'Psychology',
                'title': 'I got deep insights and practical skills',
                'content': 'This experience has been incredibly enriching, providing me with deep insights into psychological theories and practical skills that I can apply in real-world scenarios.',
                'is_active': True,
            },
            {
                'name': 'Simran Yaseen',
                'field_of_study': 'Nanoscience',
                'title': 'This journey has been rewarding',
                'content': 'This journey has been rewarding, providing me with invaluable skills and insights that I am eager to apply in my professional endeavors. The curriculum was well-structured.',
                'is_active': True,
            },
            {
                'name': 'Pavan R V',
                'field_of_study': 'Data Science',
                'title': 'Guidance and expertise were instrumental',
                'content': 'Your guidance and expertise were instrumental in my learning journey. I deeply appreciate the knowledge gained and the practical approach to complex data science concepts.',
                'is_active': True,
            },
            {
                'name': 'Aashi Makhija',
                'field_of_study': 'Digital Marketing',
                'title': 'I got to learn how to build a strong network',
                'content': "I'm happy to share that I completed my program successfully, learning various marketing strategies and how to build a strong professional network in the digital space.",
                'is_active': True,
            },
            {
                'name': 'Parthiv Kumar',
                'field_of_study': 'Cybersecurity',
                'title': 'I am grateful for this opportunity',
                'content': 'During this intensive program, I gained experience in various aspects of cybersecurity. The hands-on projects were the best part of my learning experience.',
                'is_active': True,
            },
            {
                'name': 'Prabash T',
                'field_of_study': 'Web Development',
                'title': 'This experience allowed me to learn',
                'content': 'I recently completed a rewarding program that enhanced my technical skills and provided practical experience in modern web development technologies.',
                'is_active': True,
            },
            {
                'name': 'Riya Sharma',
                'field_of_study': 'Machine Learning',
                'title': 'Outstanding curriculum and mentorship',
                'content': 'The machine learning program exceeded my expectations. The combination of theoretical knowledge and practical implementation helped me land my dream job.',
                'is_active': True,
            },
            {
                'name': 'Arjun Patel',
                'field_of_study': 'Cloud Computing',
                'title': 'Industry-relevant skills and certifications',
                'content': 'The cloud computing course provided me with industry-relevant skills and helped me achieve multiple certifications. The instructors were excellent.',
                'is_active': True,
            },
            {
                'name': 'Priya Nair',
                'field_of_study': 'UI/UX Design',
                'title': 'Creative and technical skills perfectly balanced',
                'content': 'This program perfectly balanced creative design thinking with technical implementation. I now feel confident creating user-centered digital experiences.',
                'is_active': True,
            },
            {
                'name': 'Karan Singh',
                'field_of_study': 'Artificial Intelligence',
                'title': 'Cutting-edge AI concepts made accessible',
                'content': 'The AI program made complex concepts accessible and practical. The project-based learning approach helped me understand real-world AI applications.',
                'is_active': True,
            },
            {
                'name': 'Meera Gupta',
                'field_of_study': 'Financial Technology',
                'title': 'Perfect blend of finance and technology',
                'content': 'This FinTech program provided the perfect blend of financial knowledge and technological skills. I now work at a leading financial services company.',
                'is_active': True,
            },
            {
                'name': 'Rohit Kumar',
                'field_of_study': 'Blockchain Development',
                'title': 'Future-ready blockchain skills',
                'content': 'The blockchain development course equipped me with future-ready skills. The hands-on experience with various blockchain platforms was invaluable.',
                'is_active': True,
            },
        ]

        created_count = 0
        for testimonial_data in testimonials_data:
            testimonial, created = Testimonial.objects.get_or_create(
                name=testimonial_data['name'],
                field_of_study=testimonial_data['field_of_study'],
                defaults=testimonial_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created testimonial: {testimonial.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Testimonial already exists: {testimonial.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created {created_count} new testimonials!'
            )
        )
        
        total_testimonials = Testimonial.objects.count()
        active_testimonials = Testimonial.objects.filter(is_active=True).count()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Total testimonials: {total_testimonials} ({active_testimonials} active)'
            )
        )