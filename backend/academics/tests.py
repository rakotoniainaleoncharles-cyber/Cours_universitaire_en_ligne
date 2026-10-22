from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import AcademicLevel, AcademicYear, Faculty, Subject


User = get_user_model()


class AcademicAdministrationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@test.local',
            password='AdminPass123!',
            first_name='Admin',
            last_name='Test',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.level = AcademicLevel.objects.create(name='Licence 1', code='L1', faculty=self.faculty)
        self.year = AcademicYear.objects.create(
            name='2026-2027',
            start_date='2026-09-01',
            end_date='2027-06-30',
        )

    def test_non_admin_cannot_create_academic_structure(self):
        teacher = User.objects.create_user(
            email='teacher@test.local',
            password='TeacherPass123!',
            first_name='Teacher',
            last_name='One',
            role='teacher',
        )
        self.client.force_authenticate(teacher)

        response = self.client.post('/api/faculties/', {'name': 'Droit', 'code': 'LAW'}, format='json')

        self.assertEqual(response.status_code, 403)
        self.assertFalse(Faculty.objects.filter(code='LAW').exists())

    def test_year_dates_and_single_active_year_are_validated(self):
        invalid = self.client.post('/api/academic-years/', {
            'name': 'Invalid',
            'start_date': '2027-06-30',
            'end_date': '2027-01-01',
        }, format='json')
        self.assertEqual(invalid.status_code, 400)

        first = self.client.patch(f'/api/academic-years/{self.year.pk}/', {'is_active': True}, format='json')
        self.assertEqual(first.status_code, 200)
        second = self.client.post('/api/academic-years/', {
            'name': '2027-2028',
            'start_date': '2027-09-01',
            'end_date': '2028-06-30',
            'is_active': True,
        }, format='json')
        self.assertEqual(second.status_code, 201)
        self.year.refresh_from_db()
        self.assertFalse(self.year.is_active)
        self.assertTrue(AcademicYear.objects.get(name='2027-2028').is_active)

    def test_subject_must_use_a_level_associated_with_selected_faculty(self):
        other_faculty = Faculty.objects.create(name='Droit', code='LAW')
        teacher = User.objects.create_user(
            email='teacher@test.local',
            password='TeacherPass123!',
            first_name='Teacher',
            last_name='One',
            role='teacher',
        )

        response = self.client.post('/api/subjects/', {
            'code': 'LAW101',
            'name': 'Introduction au droit',
            'faculty': other_faculty.pk,
            'level': self.level.pk,
            'academic_year': self.year.pk,
            'teacher': teacher.pk,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertFalse(Subject.objects.filter(code='LAW101').exists())

    def test_faculty_with_subjects_cannot_be_deleted(self):
        Subject.objects.create(
            code='SCI101',
            name='Biologie',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
        )

        response = self.client.delete(f'/api/faculties/{self.faculty.pk}/')

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Faculty.objects.filter(pk=self.faculty.pk).exists())

    def test_teacher_sees_admin_created_subject_only_after_it_is_assigned(self):
        teacher = User.objects.create_user(
            email='subject-teacher@test.local',
            password='TeacherPass123!',
            first_name='Subject',
            last_name='Teacher',
            role='teacher',
        )
        subject_payload = {
            'code': 'SCI-ASSIGNED-101',
            'name': 'Biologie cellulaire',
            'faculty': self.faculty.pk,
            'level': self.level.pk,
            'academic_year': self.year.pk,
            'teacher': None,
        }
        created = self.client.post('/api/subjects/', subject_payload, format='json')
        self.assertEqual(created.status_code, 201, created.data)

        teacher_client = APIClient()
        teacher_client.force_authenticate(teacher)
        unassigned = teacher_client.get('/api/teacher/subjects/')
        self.assertEqual(unassigned.status_code, 200)
        self.assertEqual(unassigned.data, [])

        assigned = self.client.patch(
            f"/api/subjects/{created.data['id']}/",
            {'teacher': teacher.pk},
            format='json',
        )
        self.assertEqual(assigned.status_code, 200, assigned.data)
        teacher_subjects = teacher_client.get('/api/teacher/subjects/')
        self.assertEqual(teacher_subjects.status_code, 200)
        self.assertEqual([item['id'] for item in teacher_subjects.data], [created.data['id']])

        course = teacher_client.post('/api/courses/', {
            'title': 'Biologie cellulaire',
            'description': 'Cours de biologie cellulaire.',
            'subject': created.data['id'],
        }, format='json')
        self.assertEqual(course.status_code, 201, course.data)

    def test_anonymous_students_can_browse_faculties_and_active_faculty_subjects(self):
        active_year = AcademicYear.objects.create(
            name='2027-2028',
            start_date='2027-09-01',
            end_date='2028-06-30',
            is_active=True,
        )
        self.faculty.name = 'Sciences avec matières'
        self.faculty.save(update_fields=['name'])
        self.level.faculty = self.faculty
        self.level.save(update_fields=['faculty'])
        subject = Subject.objects.create(
            code='SCI-ACTIVE-101',
            name='Algorithmique',
            faculty=self.faculty,
            level=self.level,
            academic_year=active_year,
        )
        Subject.objects.create(
            code='SCI-OLD-101',
            name='Ancienne matière',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
        )
        client = APIClient()
        faculty_response = client.get('/api/faculties/')
        subjects_response = client.get('/api/subjects/', {'faculty': self.faculty.pk})

        self.assertEqual(faculty_response.status_code, 200)
        self.assertIn(self.faculty.pk, [faculty['id'] for faculty in faculty_response.data])
        self.assertEqual(subjects_response.status_code, 200)
        self.assertEqual([row['id'] for row in subjects_response.data], [subject.pk])
