from io import BytesIO
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from PIL.PngImagePlugin import PngInfo
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from academics.models import AcademicLevel, AcademicYear, Faculty, Subject
from users.models import Enrollment


User = get_user_model()


def create_registration_subject():
    faculty = Faculty.objects.create(name='Sciences de démonstration', code='REG-SCI')
    level = AcademicLevel.objects.create(name='Licence 1 démo', code='REG-L1', faculty=faculty)
    year = AcademicYear.objects.create(
        name='2026-2027',
        start_date='2026-09-01',
        end_date='2027-06-30',
        is_active=True,
    )
    subject = Subject.objects.create(
        code='REG101',
        name='Matière de démonstration',
        faculty=faculty,
        level=level,
        academic_year=year,
    )
    return faculty, subject


class AdminUserManagementTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin@test.local',
            password='AdminPass123!',
            first_name='Admin',
            last_name='Test',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_public_student_registration_requires_admin_approval(self):
        client = APIClient()
        faculty, subject = create_registration_subject()
        response = client.post('/api/auth/register/', {
            'email': 'newstudent@test.local',
            'password': 'NewStudentPass123!',
            'first_name': 'New',
            'last_name': 'Student',
            'phone': '0612345678',
            'faculty': faculty.pk,
            'subject_ids': [subject.pk],
        }, format='json')

        self.assertEqual(response.status_code, 201)
        student = User.objects.get(email='newstudent@test.local')
        self.assertEqual(student.role, 'student')
        self.assertFalse(student.is_active)
        self.assertFalse(student.is_approved)
        self.assertFalse(student.is_staff)
        self.assertFalse(student.is_superuser)
        self.assertEqual(
            list(Enrollment.objects.filter(student=student).values_list('subject_id', flat=True)),
            [subject.pk],
        )
        self.assertTrue(student.check_password('NewStudentPass123!'))
        self.assertTrue(response.data['pending_approval'])
        self.assertNotIn('access', response.data)
        self.assertNotIn('refresh', response.data)
        self.assertEqual(client.post('/api/auth/login/', {
            'email': 'newstudent@test.local',
            'password': 'NewStudentPass123!',
        }, format='json').status_code, 400)

    def test_public_registration_rejects_privileged_roles_weak_passwords_and_duplicate_email(self):
        client = APIClient()
        faculty, subject = create_registration_subject()
        payload = {
            'email': 'public@test.local',
            'password': 'PublicStudentPass123!',
            'first_name': 'Public',
            'last_name': 'Student',
            'phone': '0612345678',
            'faculty': faculty.pk,
            'subject_ids': [subject.pk],
        }
        response = client.post('/api/auth/register/', {**payload, 'role': 'admin'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

        weak_password = client.post(
            '/api/auth/register/',
            {**payload, 'password': '12345678'},
            format='json',
        )
        self.assertEqual(weak_password.status_code, 400)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

        created = client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(created.status_code, 201)
        duplicate = client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(User.objects.filter(email=payload['email']).count(), 1)

    def test_student_registration_requires_subjects_from_selected_faculty(self):
        client = APIClient()
        faculty, subject = create_registration_subject()
        other_faculty = Faculty.objects.create(name='Droit démo', code='REG-LAW')
        other_level = AcademicLevel.objects.create(
            name='Licence droit démo',
            code='REG-LAW-L1',
            faculty=other_faculty,
        )
        other_subject = Subject.objects.create(
            code='REG-LAW101',
            name='Droit de démonstration',
            faculty=other_faculty,
            level=other_level,
            academic_year=subject.academic_year,
        )
        payload = {
            'email': 'wrong-faculty@test.local',
            'password': 'NewStudentPass123!',
            'first_name': 'Test',
            'last_name': 'Wrong Faculty',
            'phone': '0612345678',
            'role': 'student',
            'faculty': faculty.pk,
            'subject_ids': [other_subject.pk],
        }
        invalid = client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(invalid.status_code, 400)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())
        self.assertFalse(Enrollment.objects.exists())

        payload.update(email='no-subject@test.local', subject_ids=[])
        missing_subjects = client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(missing_subjects.status_code, 400)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_registration_rejects_phone_numbers_that_are_not_exactly_ten_digits(self):
        client = APIClient()
        faculty, subject = create_registration_subject()
        payload = {
            'email': 'phone-validation@test.local',
            'password': 'NewStudentPass123!',
            'first_name': 'Test',
            'last_name': 'Phone',
            'phone': '0612345678',
            'role': 'student',
            'faculty': faculty.pk,
            'subject_ids': [subject.pk],
        }
        for invalid_phone in ('123456789', '12345678901', '12345abc90', '+3312345678', '٠١٢٣٤٥٦٧٨٩'):
            response = client.post(
                '/api/auth/register/',
                {**payload, 'phone': invalid_phone},
                format='json',
            )
            self.assertEqual(response.status_code, 400, invalid_phone)
            self.assertIn('phone', response.data)
        self.assertFalse(User.objects.filter(email=payload['email']).exists())

    def test_admin_rejects_phone_numbers_that_are_not_exactly_ten_digits(self):
        for phone in ('123456789', '12345678901', '12345abc90'):
            response = self.client.post('/api/users/', {
                'email': f'phone-{len(phone)}-{phone[-1]}@test.local',
                'password': 'NewUserPass123!',
                'first_name': 'Test',
                'last_name': 'Phone',
                'role': 'student',
                'phone': phone,
            }, format='json')
            self.assertEqual(response.status_code, 400, phone)
            self.assertIn('phone', response.data)

    def test_public_teacher_registration_requires_admin_approval_before_login(self):
        client = APIClient()
        payload = {
            'email': 'applicant-teacher@test.local',
            'password': 'TeacherApplicantPass123!',
            'first_name': 'Applicant',
            'last_name': 'Teacher',
            'role': 'teacher',
            'phone': '',
        }
        registration = client.post('/api/auth/register/', payload, format='json')
        self.assertEqual(registration.status_code, 201)
        self.assertTrue(registration.data['pending_approval'])
        self.assertNotIn('access', registration.data)
        self.assertNotIn('refresh', registration.data)

        teacher = User.objects.get(email=payload['email'])
        self.assertEqual(teacher.role, 'teacher')
        self.assertFalse(teacher.is_active)
        self.assertFalse(teacher.is_staff)
        self.assertFalse(teacher.is_superuser)
        self.assertEqual(client.post('/api/auth/login/', {
            'email': payload['email'],
            'password': payload['password'],
        }, format='json').status_code, 400)

        activated = self.client.patch(f'/api/users/{teacher.pk}/', {'is_active': True}, format='json')
        self.assertEqual(activated.status_code, 200)
        login = client.post('/api/auth/login/', {
            'email': payload['email'],
            'password': payload['password'],
        }, format='json')
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.data['user']['role'], 'teacher')
        self.assertIn('access', login.data)

    def test_admin_can_create_teacher_and_student_accounts(self):
        for role, email in (
            ('teacher', 'teacher@test.local'),
            ('student', 'student@test.local'),
        ):
            response = self.client.post(
                '/api/users/',
                {
                    'email': email,
                    'password': 'NewUserPass123!',
                    'first_name': 'Test',
                    'last_name': role.title(),
                    'role': role,
                },
                format='json',
            )
            self.assertEqual(response.status_code, 201)
            user = User.objects.get(email=email)
            self.assertEqual(user.role, role)
            self.assertTrue(user.check_password('NewUserPass123!'))

    def test_admin_cannot_create_another_admin(self):
        response = self.client.post(
            '/api/users/',
            {
                'email': 'another-admin@test.local',
                'password': 'NewUserPass123!',
                'first_name': 'Another',
                'last_name': 'Admin',
                'role': 'admin',
            },
            format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(email='another-admin@test.local').exists())

    def test_manager_rejects_a_second_superuser(self):
        with self.assertRaisesMessage(ValueError, 'Un seul compte administrateur est autorisé.'):
            User.objects.create_superuser(
                email='another-admin@test.local',
                password='NewUserPass123!',
                first_name='Another',
                last_name='Admin',
            )

    def test_admin_can_update_and_delete_non_admin_users(self):
        teacher = User.objects.create_user(
            email='teacher@test.local',
            password='TeacherPass123!',
            first_name='Teacher',
            last_name='One',
            role='teacher',
        )

        update_response = self.client.patch(
            f'/api/users/{teacher.pk}/',
            {'role': 'student'},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        teacher.refresh_from_db()
        self.assertEqual(teacher.role, 'student')

        delete_response = self.client.delete(f'/api/users/{teacher.pk}/')
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(User.objects.filter(pk=teacher.pk).exists())

    def test_unique_admin_account_cannot_be_deleted_or_demoted(self):
        update_response = self.client.patch(
            f'/api/users/{self.admin.pk}/',
            {'role': 'student'},
            format='json',
        )
        self.assertEqual(update_response.status_code, 200)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, 'admin')

        delete_response = self.client.delete(f'/api/users/{self.admin.pk}/')
        self.assertEqual(delete_response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.admin.pk, role='admin').exists())

    def test_admin_dashboard_uses_database_counts_and_recent_users(self):
        User.objects.create_user(
            email='student@test.local',
            password='StudentPass123!',
            first_name='Student',
            last_name='One',
            role='student',
        )

        response = self.client.get('/api/admin/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['student_count'], 1)
        self.assertEqual(response.data['teacher_count'], 0)
        self.assertEqual(response.data['active_user_count'], 2)
        self.assertEqual(response.data['recent_users'][0]['email'], 'student@test.local')

    def test_admin_can_disable_users_and_cannot_disable_the_admin_account(self):
        student = User.objects.create_user(
            email='student@test.local',
            password='StudentPass123!',
            first_name='Student',
            last_name='One',
            role='student',
        )

        response = self.client.patch(f'/api/users/{student.pk}/', {'is_active': False}, format='json')
        self.assertEqual(response.status_code, 200)
        student.refresh_from_db()
        self.assertFalse(student.is_active)

        admin_response = self.client.patch(f'/api/users/{self.admin.pk}/', {'is_active': False}, format='json')
        self.assertEqual(admin_response.status_code, 400)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_non_admin_cannot_access_admin_dashboard_or_audit_log(self):
        teacher = User.objects.create_user(
            email='teacher@test.local',
            password='TeacherPass123!',
            first_name='Teacher',
            last_name='One',
            role='teacher',
        )
        self.client.force_authenticate(teacher)

        self.assertEqual(self.client.get('/api/admin/dashboard/').status_code, 403)
        self.assertEqual(self.client.get('/api/admin/audit-logs/').status_code, 403)

    def test_admin_can_search_by_unique_student_matricule(self):
        created = self.client.post('/api/users/', {
            'email': 'student@test.local',
            'password': 'StudentPass123!',
            'first_name': 'Student',
            'last_name': 'One',
            'role': 'student',
            'matricule': 'STU-2026-001',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data['matricule'], 'STU-2026-001')

        audit_response = self.client.get('/api/admin/audit-logs/')
        self.assertEqual(audit_response.status_code, 200)
        self.assertEqual(audit_response.data[0]['action'], 'create')
        self.assertNotIn('password', str(audit_response.data).lower())

        response = self.client.get('/api/users/', {'search': 'STU-2026-001'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([user['email'] for user in response.data], ['student@test.local'])

        duplicate = self.client.post('/api/users/', {
            'email': 'student2@test.local',
            'password': 'StudentPass123!',
            'first_name': 'Student',
            'last_name': 'Two',
            'role': 'student',
            'matricule': 'STU-2026-001',
        }, format='json')
        self.assertEqual(duplicate.status_code, 400)

    def test_refresh_token_mistaken_for_access_token_can_be_recovered(self):
        refresh = RefreshToken.for_user(self.admin)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh}')
        invalid_access_response = self.client.get('/api/admin/dashboard/')
        self.assertEqual(invalid_access_response.status_code, 401)
        self.assertEqual(invalid_access_response.data['code'], 'token_not_valid')

        refresh_response = self.client.post(
            '/api/auth/token/refresh/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, 200)
        self.assertIn('access', refresh_response.data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh_response.data['access']}")
        recovered_response = self.client.get('/api/admin/dashboard/')
        self.assertEqual(recovered_response.status_code, 200)

    def test_jwt_session_check_preserves_identity_and_enforces_role_permissions(self):
        student = User.objects.create_user(
            email='jwt-student@test.local',
            password='StudentPass123!',
            first_name='JWT',
            last_name='Student',
            role='student',
        )
        token = RefreshToken.for_user(student)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')

        session_response = client.get('/api/auth/me/')
        self.assertEqual(session_response.status_code, 200)
        self.assertEqual(session_response.data['email'], student.email)
        self.assertEqual(session_response.data['role'], 'student')
        self.assertEqual(client.get('/api/admin/dashboard/').status_code, 403)
        self.assertEqual(client.get('/api/teacher/dashboard/').status_code, 403)

        teacher = User.objects.create_user(
            email='jwt-teacher@test.local',
            password='TeacherPass123!',
            first_name='JWT',
            last_name='Teacher',
            role='teacher',
        )
        teacher_token = RefreshToken.for_user(teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {teacher_token.access_token}')
        teacher_session_response = client.get('/api/auth/me/')
        self.assertEqual(teacher_session_response.status_code, 200)
        self.assertEqual(teacher_session_response.data['email'], teacher.email)
        self.assertEqual(teacher_session_response.data['role'], 'teacher')
        self.assertEqual(client.get('/api/admin/dashboard/').status_code, 403)
        self.assertEqual(client.get('/api/student/dashboard/').status_code, 403)

    def test_login_tokens_and_session_endpoint_keep_each_users_identity(self):
        for role, email, password in (
            ('teacher', 'login-teacher@test.local', 'TeacherPass123!'),
            ('student', 'login-student@test.local', 'StudentPass123!'),
        ):
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=role.title(),
                last_name='Login',
                role=role,
            )
            login_response = APIClient().post(
                '/api/auth/login/',
                {'email': email, 'password': password},
                format='json',
            )
            self.assertEqual(login_response.status_code, 200)
            self.assertEqual(login_response.data['user']['email'], user.email)
            self.assertEqual(login_response.data['user']['role'], role)

            client = APIClient()
            client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_response.data['access']}")
            session_response = client.get('/api/auth/me/')
            self.assertEqual(session_response.status_code, 200)
            self.assertEqual(session_response.data['email'], user.email)
            self.assertEqual(session_response.data['role'], role)

    def test_logout_blacklists_the_refresh_token(self):
        refresh = RefreshToken.for_user(self.admin)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')

        logout_response = client.post(
            '/api/auth/logout/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(logout_response.status_code, 200)

        refresh_response = client.post(
            '/api/auth/token/refresh/',
            {'refresh': str(refresh)},
            format='json',
        )
        self.assertEqual(refresh_response.status_code, 401)


class UserAvatarTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='avatar-user@test.local',
            password='AvatarPass123!',
            first_name='Photo',
            last_name='User',
            role='teacher',
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_authenticated_users_can_upload_and_view_profile_photos(self):
        image_buffer = BytesIO()
        Image.new('RGB', (12, 12), color='purple').save(image_buffer, format='PNG')
        image_bytes = image_buffer.getvalue()

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            upload = SimpleUploadedFile('profil.png', image_bytes, content_type='image/png')
            response = self.client.patch(
                '/api/auth/profile/',
                {'avatar': upload, 'email': 'changed@test.local'},
                format='multipart',
            )
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data['email'], self.user.email)
            self.assertTrue(response.data['avatar_url'].endswith(f'/api/users/{self.user.pk}/avatar/'))
            self.assertNotIn('avatar', response.data)

            avatar = self.client.get(response.data['avatar_url'])
            self.assertEqual(avatar.status_code, 200)
            self.assertEqual(avatar['Content-Type'], 'image/png')
            self.assertEqual(b''.join(avatar.streaming_content), image_bytes)

            admin = User.objects.create_superuser(
                email='avatar-admin@test.local',
                password='AdminPass123!',
                first_name='Avatar',
                last_name='Admin',
            )
            admin_client = APIClient()
            admin_client.force_authenticate(admin)
            listed_user = next(
                row for row in admin_client.get('/api/users/').data
                if row['id'] == self.user.pk
            )
            self.assertEqual(listed_user['avatar_url'], response.data['avatar_url'])

        anonymous = APIClient()
        self.assertEqual(anonymous.get(f'/api/users/{self.user.pk}/avatar/').status_code, 401)

    def test_profile_photo_upload_rejects_invalid_images(self):
        invalid = self.client.patch(
            '/api/auth/profile/',
            {'avatar': SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')},
            format='multipart',
        )
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('avatar', invalid.data)

    def test_profile_photo_upload_accepts_files_over_five_megabytes(self):
        image_buffer = BytesIO()
        metadata = PngInfo()
        metadata.add_text('Comment', 'x' * (5 * 1024 * 1024))
        Image.new('RGB', (12, 12), color='purple').save(image_buffer, format='PNG', pnginfo=metadata)
        image_bytes = image_buffer.getvalue()
        self.assertGreater(len(image_bytes), 5 * 1024 * 1024)

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            response = self.client.patch(
                '/api/auth/profile/',
                {'avatar': SimpleUploadedFile('large.png', image_bytes, content_type='image/png')},
                format='multipart',
            )

        self.assertEqual(response.status_code, 200, response.data)
