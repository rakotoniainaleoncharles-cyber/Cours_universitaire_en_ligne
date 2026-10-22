from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
from getpass import getpass
from io import BytesIO
import sys

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from academics.models import AcademicLevel, AcademicYear, Faculty, Subject
from courses.models import Assignment, Course, Lesson, LessonProgress, Material, Submission
from users.models import Enrollment


def build_demo_pdf(title):
    safe_title = title.encode('ascii', errors='replace').decode('ascii')
    safe_title = safe_title.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
    stream = f'BT /F1 18 Tf 72 720 Td ({safe_title}) Tj ET'.encode('ascii')
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
        b'/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>',
        b'<< /Length %d >>\nstream\n%s\nendstream' % (len(stream), stream),
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    output = BytesIO()
    output.write(b'%PDF-1.4\n')
    offsets = [0]
    for index, content in enumerate(objects, start=1):
        offsets.append(output.tell())
        output.write(f'{index} 0 obj\n'.encode('ascii'))
        output.write(content)
        output.write(b'\nendobj\n')
    xref_offset = output.tell()
    output.write(f'xref\n0 {len(offsets)}\n'.encode('ascii'))
    output.write(b'0000000000 65535 f \n')
    for offset in offsets[1:]:
        output.write(f'{offset:010d} 00000 n \n'.encode('ascii'))
    output.write(
        f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n'
        f'startxref\n{xref_offset}\n%%EOF\n'.encode('ascii')
    )
    return output.getvalue()


class Command(BaseCommand):
    help = 'Ajoute des comptes et contenus de démonstration sans modifier les données existantes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Mot de passe initial des nouveaux comptes démo (sinon demandé de façon masquée).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        user_specs = (
            ('demo.prof.info@unistra.fr', 'Camille', 'Martin', 'teacher', 'DEMO-PROF-001', '0600000001', True, True),
            ('demo.prof.gestion@unistra.fr', 'Nora', 'Bernard', 'teacher', 'DEMO-PROF-002', '0600000002', True, True),
            ('demo.prof.attente@unistra.fr', 'Jules', 'Simon', 'teacher', 'DEMO-PROF-003', '0600000003', False, False),
            ('demo.etudiant1@unistra.fr', 'Alex', 'Petit', 'student', 'DEMO-ETU-001', '0600000011', True, True),
            ('demo.etudiant2@unistra.fr', 'Lina', 'Robert', 'student', 'DEMO-ETU-002', '0600000012', True, True),
            ('demo.etudiant3@unistra.fr', 'Samir', 'Moreau', 'student', 'DEMO-ETU-003', '0600000013', True, True),
        )
        missing_users = [
            email for email, *_ in user_specs
            if not User.objects.filter(email=email).exists()
        ]
        password = options['password']
        if missing_users and not password:
            if not sys.stdin.isatty():
                raise CommandError(
                    'Des comptes démo doivent être créés. Relancez la commande dans un terminal interactif '
                    'ou fournissez --password. Aucun compte n’a été créé.'
                )
            password = getpass('Mot de passe initial des nouveaux comptes démo : ')
            confirmation = getpass('Confirmez le mot de passe : ')
            if password != confirmation:
                raise CommandError('Les mots de passe ne correspondent pas. Aucun compte n’a été créé.')
        if missing_users:
            try:
                validate_password(password)
            except ValidationError as error:
                raise CommandError('; '.join(error.messages)) from error

        self.created_counts = defaultdict(int)
        self.updated_counts = defaultdict(int)
        users = {}
        for email, first_name, last_name, role, matricule, phone, is_active, is_approved in user_specs:
            user, created, updated = self.get_demo_user(
                User,
                email,
                password,
                first_name,
                last_name,
                role,
                matricule,
                phone,
                is_active,
                is_approved,
            )
            users[email] = user
            self.record('comptes', created, updated)
        teachers = {
            'info': users['demo.prof.info@unistra.fr'],
            'gestion': users['demo.prof.gestion@unistra.fr'],
        }
        students = [
            users['demo.etudiant1@unistra.fr'],
            users['demo.etudiant2@unistra.fr'],
            users['demo.etudiant3@unistra.fr'],
        ]
        if any(not teacher.is_active or not teacher.is_approved for teacher in teachers.values()):
            raise CommandError(
                'Un compte professeur de démonstration déjà présent est inactif ou en attente. '
                'Aucun compte existant n’a été réactivé.'
            )
        if any(not student.is_active or not student.is_approved for student in students):
            raise CommandError(
                'Un compte étudiant de démonstration déjà présent est inactif ou en attente. '
                'Aucun compte existant n’a été réactivé.'
            )

        info_faculty, info_faculty_created = Faculty.objects.get_or_create(
            code='DEMO-INFO',
            defaults={
                'name': 'Filière Informatique (démo)',
                'description': 'Exemple de filière pour tester le portail académique.',
            },
        )
        gestion_faculty, gestion_faculty_created = Faculty.objects.get_or_create(
            code='DEMO-GEST',
            defaults={
                'name': 'Filière Gestion (démo)',
                'description': 'Exemple de filière pour tester le portail académique.',
            },
        )
        self.record('filières', info_faculty_created)
        self.record('filières', gestion_faculty_created)

        start_year = timezone.localdate().year if timezone.localdate().month >= 9 else timezone.localdate().year - 1
        year_name = f'{start_year}-{start_year + 1}'
        year = AcademicYear.objects.filter(is_active=True).first()
        year_created = False
        if year is None:
            year, year_created = AcademicYear.objects.get_or_create(
                name=year_name,
                defaults={
                    'start_date': date(start_year, 9, 1),
                    'end_date': date(start_year + 1, 6, 30),
                    'is_active': True,
                },
            )
        self.record('années académiques', year_created)

        levels = {}
        for key, faculty, name, code in (
            ('info_l1', info_faculty, 'Licence 1 Informatique (démo)', 'DEMO-I-L1'),
            ('info_l2', info_faculty, 'Licence 2 Informatique (démo)', 'DEMO-I-L2'),
            ('gestion_l1', gestion_faculty, 'Licence 1 Gestion (démo)', 'DEMO-G-L1'),
        ):
            levels[key], created = AcademicLevel.objects.get_or_create(
                code=code,
                defaults={'name': name, 'faculty': faculty},
            )
            self.record('niveaux', created)

        subjects = []
        subject_data = (
            ('DEMO-PY101', 'Programmation Python', info_faculty, levels['info_l1'], teachers['info'],
             'Bases de Python, algorithmes et résolution de problèmes.'),
            ('DEMO-WEB101', 'Développement web', info_faculty, levels['info_l1'], teachers['info'],
             'HTML, CSS, JavaScript et conception d’interfaces web.'),
            ('DEMO-DB201', 'Bases de données', info_faculty, levels['info_l2'], teachers['info'],
             'Modélisation relationnelle, SQL et conception de schémas.'),
            ('DEMO-ALGO201', 'Algorithmique avancée', info_faculty, levels['info_l2'], teachers['info'],
             'Structures de données et analyse de complexité.'),
            ('DEMO-MKT101', 'Introduction au marketing', gestion_faculty, levels['gestion_l1'], teachers['gestion'],
             'Étude de marché, segmentation et stratégie marketing.'),
            ('DEMO-GEST101', 'Comptabilité générale', gestion_faculty, levels['gestion_l1'], teachers['gestion'],
             'Principes comptables, bilan et compte de résultat.'),
        )
        for code, name, faculty, level, teacher, description in subject_data:
            subject, created = Subject.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'faculty': faculty,
                    'level': level,
                    'academic_year': year,
                    'teacher': teacher,
                    'description': description,
                },
            )
            self.record('matières', created)
            if subject.teacher_id is None:
                subject.teacher = teacher
                subject.save(update_fields=['teacher'])
                self.updated_counts['matières'] += 1
            if (
                subject.faculty_id != faculty.id
                or subject.level_id != level.id
                or subject.academic_year_id != year.id
            ):
                raise CommandError(
                    f'La matière de démonstration {code} existe déjà avec des relations différentes. '
                    'Aucune donnée n’a été supprimée.'
                )
            subjects.append(subject)

        course_data = (
            ('demo-python-fondamentaux', 'Python : les fondamentaux', subjects[0],
             'Variables, conditions, boucles et fonctions avec des exercices pratiques.'),
            ('demo-web-premiers-pas', 'Créer sa première page web', subjects[1],
             'Construire une page accessible et responsive avec HTML, CSS et JavaScript.'),
            ('demo-sql-modelisation', 'Modélisation et SQL', subjects[2],
             'Concevoir un modèle relationnel et interroger des données avec SQL.'),
            ('demo-algorithmes', 'Algorithmes et structures de données', subjects[3],
             'Comparer des algorithmes et choisir les structures adaptées.'),
            ('demo-marketing', 'Les bases du marketing', subjects[4],
             'Analyser un marché et élaborer une proposition de valeur.'),
            ('demo-comptabilite', 'Lire les états financiers', subjects[5],
             'Comprendre les écritures courantes, le bilan et le compte de résultat.'),
        )
        now = timezone.now()
        courses = {}
        for slug, title, subject, description in course_data:
            course, created = Course.objects.get_or_create(
                slug=slug,
                defaults={
                    'title': title,
                    'description': description,
                    'objectives': f'Comprendre les notions essentielles de {subject.name.lower()} et les appliquer sur des cas pratiques.',
                    'subject': subject,
                    'teacher': subject.teacher or teachers['info'],
                    'status': Course.Status.PUBLISHED,
                },
            )
            self.record('cours', created)
            if course.subject_id != subject.id or course.teacher_id != subject.teacher_id:
                raise CommandError(
                    f'Le cours de démonstration {slug} existe déjà avec une matière ou un enseignant différent. '
                    'Aucune donnée n’a été supprimée.'
                )
            courses[subject.pk] = course
            for order, lesson_title, lesson_description in (
                (1, f'Introduction — {subject.name}', f'Découvrir les objectifs et le vocabulaire de {subject.name.lower()}.'),
                (2, f'Exercices pratiques — {subject.name}', 'Appliquer les notions du cours à des exercices guidés.'),
            ):
                lesson, created = Lesson.objects.get_or_create(
                    course=course,
                    title=lesson_title,
                    defaults={
                        'description': lesson_description,
                        'content': (
                            f'# {lesson_title}\n\n{lesson_description}\n\n'
                            'À retenir : prenez des notes, réalisez les exercices et vérifiez vos réponses '
                            'avant de passer à la leçon suivante.'
                        ),
                        'order': order,
                        'status': Lesson.Status.PUBLISHED,
                    },
                )
                self.record('leçons', created)
                if order == 1:
                    material, created = Material.objects.get_or_create(
                        course=course,
                        title=f'Fiche de cours — {subject.name}',
                        defaults={
                            'lesson': lesson,
                            'description': 'Fiche PDF de démonstration téléchargeable.',
                            'uploaded_by': course.teacher,
                        },
                    )
                    self.record('ressources', created)
                    if created:
                        material.file.save(
                            f'{slug}-fiche.pdf',
                            ContentFile(build_demo_pdf(f'Fiche de cours - {subject.name}')),
                            save=True,
                        )
                    elif not material.file:
                        material.file.save(
                            f'{slug}-fiche.pdf',
                            ContentFile(build_demo_pdf(f'Fiche de cours - {subject.name}')),
                            save=True,
                        )
                        self.updated_counts['ressources'] += 1
            assignment, created = Assignment.objects.get_or_create(
                course=course,
                title=f'Exercice — {subject.name}',
                defaults={
                    'instructions': (
                        f'Réalisez un court travail pratique sur {subject.name.lower()}. '
                        'Présentez votre démarche, vos résultats et une conclusion.'
                    ),
                    'due_at': now + timedelta(days=21),
                    'is_published': True,
                },
            )
            self.record('devoirs', created)

        enrollments = []
        for student_index, student in enumerate(students):
            for subject_index, subject in enumerate(subjects):
                if (subject_index + student_index) % 3 == 0:
                    enrollment, created = Enrollment.objects.get_or_create(
                        student=student,
                        subject=subject,
                        academic_year=subject.academic_year,
                        defaults={'status': Enrollment.Status.ACTIVE},
                    )
                    self.record('inscriptions', created)
                    enrollments.append((student_index, student, subject, enrollment))

        for student_index, student, subject, _enrollment in enrollments:
            course = courses[subject.pk]
            lessons = list(course.lessons.order_by('order', 'pk'))
            if not lessons:
                continue
            _, created = LessonProgress.objects.get_or_create(
                student=student,
                lesson=lessons[0],
                defaults={'completed_at': now - timedelta(days=student_index + 1)},
            )
            self.record('progressions', created)
            if len(lessons) > 1 and student_index % 2 == 0:
                _, created = LessonProgress.objects.get_or_create(
                    student=student,
                    lesson=lessons[1],
                    defaults={'completed_at': None},
                )
                self.record('progressions', created)

            assignment = course.assignments.order_by('pk').first()
            if assignment is None:
                continue
            submission, created = Submission.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    'file': ContentFile(
                        build_demo_pdf(f'Travail de {student.get_full_name()} - {subject.name}'),
                        name=f'demo-{student.pk}-{assignment.pk}.pdf',
                    ),
                    'comment': 'Remise de démonstration pour vérifier le parcours de correction.',
                    'grade': Decimal('14.00') + Decimal(student_index * 2),
                    'feedback': 'Travail sérieux. Pensez à détailler davantage les étapes de votre raisonnement.',
                },
            )
            if created:
                submission.graded_at = timezone.now()
                submission.save(update_fields=['graded_at']                )
                self.record('remises notées', created)

        self.stdout.write(self.style.SUCCESS('Données de démonstration vérifiées.'))
        self.stdout.write('Créés pendant cette exécution :')
        for label, count in sorted(self.created_counts.items()):
            if count:
                self.stdout.write(f'  {label} : {count}')
        if not any(self.created_counts.values()):
            self.stdout.write('  aucun doublon créé')
        self.stdout.write('Mis à jour sans remplacer de données existantes :')
        for label, count in sorted(self.updated_counts.items()):
            if count:
                self.stdout.write(f'  {label} : {count}')
        if not any(self.updated_counts.values()):
            self.stdout.write('  aucun')
        self.stdout.write(
            f'Présents pour le parcours de démonstration : {len(teachers)} professeurs actifs, '
            f'1 professeur en attente, {len(students)} étudiants, {len(subjects)} matières, '
            f'{len(course_data)} cours, {Lesson.objects.filter(course__slug__startswith="demo-").count()} leçons, '
            f'{Assignment.objects.filter(course__slug__startswith="demo-").count()} devoirs, '
            f'{Material.objects.filter(course__slug__startswith="demo-").count()} ressources, '
            f'{LessonProgress.objects.filter(lesson__course__slug__startswith="demo-").count()} progressions, '
            f'{Submission.objects.filter(assignment__course__slug__startswith="demo-").count()} remises.'
        )
        self.stdout.write('Comptes de démonstration :')
        self.stdout.write('  Professeurs actifs : demo.prof.info@unistra.fr, demo.prof.gestion@unistra.fr')
        self.stdout.write('  Professeur en attente : demo.prof.attente@unistra.fr')
        self.stdout.write(f'  Étudiants : demo.etudiant1@unistra.fr, demo.etudiant2@unistra.fr, demo.etudiant3@unistra.fr')
        self.stdout.write(self.style.WARNING(
            'Aucun administrateur n’est créé ni modifié. Les mots de passe existants ne sont jamais remplacés.'
        ))

    def record(self, label, created=False, updated=False):
        self.created_counts[label] += int(created)
        self.updated_counts[label] += int(updated)

    @staticmethod
    def get_demo_user(
        User, email, password, first_name, last_name, role, matricule, phone, is_active, is_approved,
    ):
        user = User.objects.filter(email=email).first()
        if user:
            if user.role != role:
                raise CommandError(
                    f'{email} existe déjà avec le rôle "{user.role}", attendu "{role}". '
                    'Aucune donnée n’a été modifiée.'
                )
            changed_fields = []
            if not user.matricule:
                user.matricule = matricule
                changed_fields.append('matricule')
            if not user.phone:
                user.phone = phone
                changed_fields.append('phone')
            if changed_fields:
                user.save(update_fields=changed_fields)
            return user, False, bool(changed_fields)
        return User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=role,
            matricule=matricule,
            phone=phone,
            is_active=is_active,
            is_approved=is_approved,
        ), True, False
