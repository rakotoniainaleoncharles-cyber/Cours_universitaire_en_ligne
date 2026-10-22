from io import StringIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings
from rest_framework.test import APIClient

from academics.models import AcademicLevel, AcademicYear, Faculty, Subject
from courses.models import LessonProgress, Submission
from .models import Enrollment


User = get_user_model()


class EnrollmentAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@test.local',
            password='AdminPass123!',
            first_name='Admin',
            last_name='Test',
        )
        self.student = User.objects.create_user(
            email='student@test.local',
            password='StudentPass123!',
            first_name='Student',
            last_name='One',
            role='student',
        )
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.level = AcademicLevel.objects.create(name='Licence 1', code='L1')
        self.year = AcademicYear.objects.create(
            name='2026-2027',
            start_date='2026-09-01',
            end_date='2027-06-30',
        )
        self.subject = Subject.objects.create(
            code='SCI101',
            name='Biologie',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_admin_can_create_and_deactivate_enrollment_without_losing_history(self):
        created = self.client.post('/api/enrollments/', {
            'student': self.student.pk,
            'subject': self.subject.pk,
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        enrollment = Enrollment.objects.get()
        self.assertEqual(enrollment.academic_year, self.year)
        self.assertEqual(enrollment.status, Enrollment.Status.ACTIVE)

        updated = self.client.patch(
            f'/api/enrollments/{enrollment.pk}/',
            {'status': Enrollment.Status.INACTIVE},
            format='json',
        )
        self.assertEqual(updated.status_code, 200)
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.academic_year, self.year)
        self.assertEqual(enrollment.status, Enrollment.Status.INACTIVE)

    def test_duplicate_enrollment_is_rejected(self):
        Enrollment.objects.create(
            student=self.student,
            subject=self.subject,
            academic_year=self.year,
        )

        response = self.client.post('/api/enrollments/', {
            'student': self.student.pk,
            'subject': self.subject.pk,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Enrollment.objects.count(), 1)


class DemoSeedCommandTests(TestCase):
    def test_seed_command_creates_usable_demo_data_and_is_idempotent(self):
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            admin = User.objects.create_superuser(
                email='admin@test.local',
                password='AdminSecurePass2026!',
                first_name='Admin',
                last_name='Test',
            )
            with patch('users.management.commands.seed_demo_data.sys.stdin') as stdin:
                stdin.isatty.return_value = False
                with self.assertRaises(CommandError):
                    call_command('seed_demo_data', stdout=StringIO())
            self.assertFalse(User.objects.filter(email__startswith='demo.').exists())
            output = StringIO()
            call_command(
                'seed_demo_data',
                password='DemoSeedPass2026!Safe',
                stdout=output,
            )

            self.assertEqual(User.objects.filter(email__startswith='demo.').count(), 6)
            self.assertEqual(User.objects.filter(role='admin').count(), 1)
            admin.refresh_from_db()
            self.assertTrue(admin.check_password('AdminSecurePass2026!'))
            self.assertIn('Créés pendant cette exécution', output.getvalue())
            self.assertEqual(Faculty.objects.filter(code__startswith='DEMO-').count(), 2)
            self.assertEqual(AcademicLevel.objects.filter(code__startswith='DEMO-').count(), 3)
            self.assertEqual(Subject.objects.filter(code__startswith='DEMO-').count(), 6)
            self.assertEqual(Enrollment.objects.filter(student__email__startswith='demo.').count(), 6)
            pending_teacher = User.objects.get(email='demo.prof.attente@unistra.fr')
            self.assertEqual(pending_teacher.role, 'teacher')
            self.assertFalse(pending_teacher.is_active)
            self.assertFalse(pending_teacher.is_approved)
            self.assertIsNotNone(pending_teacher.matricule)
            self.assertTrue(pending_teacher.phone)

            from courses.models import Assignment, Course, Lesson, Material

            self.assertEqual(Course.objects.filter(slug__startswith='demo-').count(), 6)
            self.assertEqual(Lesson.objects.filter(course__slug__startswith='demo-').count(), 12)
            self.assertEqual(Assignment.objects.filter(course__slug__startswith='demo-').count(), 6)
            self.assertEqual(Material.objects.filter(course__slug__startswith='demo-').count(), 6)
            self.assertEqual(LessonProgress.objects.filter(lesson__course__slug__startswith='demo-').count(), 10)
            self.assertEqual(Submission.objects.filter(assignment__course__slug__startswith='demo-').count(), 6)
            for submission in Submission.objects.filter(assignment__course__slug__startswith='demo-'):
                self.assertIsNotNone(submission.grade)
                self.assertIsNotNone(submission.graded_at)
                self.assertGreaterEqual(submission.graded_at, submission.submitted_at)
            material = Material.objects.filter(course__slug__startswith='demo-').first()
            material.file.open('rb')
            self.assertTrue(material.file.read().startswith(b'%PDF-1.4'))
            material.file.close()

            demo_student = User.objects.get(email='demo.etudiant1@unistra.fr')
            self.assertTrue(demo_student.is_active)
            self.assertTrue(demo_student.is_approved)
            self.assertTrue(demo_student.check_password('DemoSeedPass2026!Safe'))
            self.assertTrue(demo_student.matricule)
            self.assertTrue(demo_student.phone)

            client = APIClient()
            teacher_login = client.post('/api/auth/login/', {
                'email': 'demo.prof.info@unistra.fr',
                'password': 'DemoSeedPass2026!Safe',
            }, format='json')
            self.assertEqual(teacher_login.status_code, 200)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {teacher_login.data['access']}")
            self.assertEqual(len(client.get('/api/courses/').data), 4)
            teacher_dashboard = client.get('/api/teacher/dashboard/')
            self.assertEqual(teacher_dashboard.status_code, 200)
            self.assertEqual(teacher_dashboard.data['student_count'], 3)
            self.assertEqual(len(client.get('/api/teacher/students/').data), 3)

            student_login = client.post('/api/auth/login/', {
                'email': 'demo.etudiant1@unistra.fr',
                'password': 'DemoSeedPass2026!Safe',
            }, format='json')
            self.assertEqual(student_login.status_code, 200)
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {student_login.data['access']}")
            self.assertEqual(len(client.get('/api/courses/').data), 2)
            student_dashboard = client.get('/api/student/dashboard/')
            self.assertEqual(student_dashboard.status_code, 200)
            self.assertEqual(student_dashboard.data['course_count'], 2)
            self.assertEqual(student_dashboard.data['completed_lesson_count'], 2)
            self.assertEqual(student_dashboard.data['pending_assignment_count'], 0)
            progress_response = client.get('/api/student/progress/')
            self.assertEqual(progress_response.status_code, 200)
            self.assertEqual(len(progress_response.data), 4)
            assignments = client.get('/api/assignments/')
            self.assertEqual(assignments.status_code, 200)
            self.assertEqual(len(assignments.data), 2)
            submissions_response = client.get(
                f"/api/assignments/{assignments.data[0]['id']}/submissions/",
            )
            self.assertEqual(submissions_response.status_code, 200)
            self.assertEqual(len(submissions_response.data), 1)
            self.assertTrue(submissions_response.data[0]['is_graded'])
            self.assertIsNotNone(submissions_response.data[0]['grade'])

            client.force_authenticate(admin)
            admin_dashboard = client.get('/api/admin/dashboard/')
            self.assertEqual(admin_dashboard.status_code, 200)
            self.assertEqual(admin_dashboard.data['student_count'], 3)
            self.assertEqual(admin_dashboard.data['teacher_count'], 3)
            self.assertEqual(admin_dashboard.data['submission_count'], 6)

            demo_student.set_password('StudentChangedPass2026!Safe')
            demo_student.save(update_fields=['password'])
            call_command('seed_demo_data', password='DemoSeedPass2026!Safe', stdout=StringIO())
            demo_student.refresh_from_db()
            self.assertTrue(demo_student.check_password('StudentChangedPass2026!Safe'))
            self.assertFalse(demo_student.check_password('DemoSeedPass2026!Safe'))
            self.assertEqual(User.objects.filter(email__startswith='demo.').count(), 6)
            self.assertEqual(Enrollment.objects.filter(student__email__startswith='demo.').count(), 6)
            self.assertEqual(Submission.objects.filter(assignment__course__slug__startswith='demo-').count(), 6)
