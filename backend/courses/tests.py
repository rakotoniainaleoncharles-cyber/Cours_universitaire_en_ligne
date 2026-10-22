from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from academics.models import AcademicLevel, AcademicYear, Faculty, Subject
from courses.models import (
    Announcement,
    Assignment,
    Course,
    Lesson,
    LessonProgress,
    Material,
    SocialPost,
    Submission,
)
from users.models import Enrollment


class TeacherWorkspaceTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            email='teacher@test.local',
            password='TeacherPass123!',
            first_name='Tessa',
            last_name='Teacher',
            role='teacher',
        )
        self.other_teacher = User.objects.create_user(
            email='other@test.local',
            password='OtherPass123!',
            first_name='Oliver',
            last_name='Other',
            role='teacher',
        )
        self.student = User.objects.create_user(
            email='student@test.local',
            password='StudentPass123!',
            first_name='Sam',
            last_name='Student',
            role='student',
        )
        self.faculty = Faculty.objects.create(name='Informatique', code='INFO')
        self.level = AcademicLevel.objects.create(name='Licence 1', code='L1')
        self.year = AcademicYear.objects.create(
            name='2026-2027',
            start_date='2026-09-01',
            end_date='2027-06-30',
        )
        self.subject = Subject.objects.create(
            code='INFO101',
            name='Introduction à l’informatique',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
            teacher=self.teacher,
        )
        self.other_subject = Subject.objects.create(
            code='INFO202',
            name='Réseaux',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
            teacher=self.other_teacher,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.teacher)

    def make_course(self, teacher=None, subject=None, status=Course.Status.PUBLISHED):
        teacher = teacher or self.teacher
        subject = subject or self.subject
        return Course.objects.create(
            title=f'Cours {subject.code}',
            slug=f'cours-{subject.code.lower()}-{Course.objects.count()}',
            description='Description du cours',
            subject=subject,
            teacher=teacher,
            status=status,
        )

    def test_teacher_dashboard_and_subjects_are_database_backed_and_scoped(self):
        course = self.make_course()
        Lesson.objects.create(course=course, title='Leçon 1', content='Contenu', status=Lesson.Status.PUBLISHED)
        Enrollment.objects.create(student=self.student, subject=self.subject)
        response = self.client.get('/api/teacher/dashboard/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['subject_count'], 1)
        self.assertEqual(response.data['course_count'], 1)
        self.assertEqual(response.data['lesson_count'], 1)
        self.assertEqual(response.data['student_count'], 1)

        subjects_response = self.client.get('/api/teacher/subjects/')
        self.assertEqual(subjects_response.status_code, 200)
        self.assertEqual(len(subjects_response.data), 1)
        self.assertEqual(subjects_response.data[0]['student_count'], 1)

    def test_teacher_can_only_create_course_for_an_assigned_subject(self):
        allowed = self.client.post('/api/courses/', {
            'title': 'Algorithmes',
            'description': 'Cours de base',
            'objectives': 'Comprendre les algorithmes',
            'subject': self.subject.pk,
            'status': Course.Status.DRAFT,
        }, format='json')
        self.assertEqual(allowed.status_code, 201)
        self.assertEqual(allowed.data['slug'], 'algorithmes')

        denied = self.client.post('/api/courses/', {
            'title': 'Cours interdit',
            'description': 'Une autre matière',
            'subject': self.other_subject.pk,
        }, format='json')
        self.assertEqual(denied.status_code, 400)

        other_course = self.make_course(teacher=self.other_teacher, subject=self.other_subject)
        self.assertFalse(any(item['id'] == other_course.pk for item in self.client.get('/api/courses/').data))
        self.assertEqual(self.client.get(f'/api/courses/{other_course.pk}/').status_code, 404)

    def test_students_only_receive_published_lessons_and_course_materials(self):
        course = self.make_course(status=Course.Status.DRAFT)
        published_lesson = Lesson.objects.create(
            course=course, title='Publiée', content='Visible', status=Lesson.Status.PUBLISHED,
        )
        Lesson.objects.create(course=course, title='Brouillon', content='Privé')
        published_course = self.make_course(subject=self.subject)
        published_doc = Material.objects.create(
            course=published_course,
            title='Support',
            file=SimpleUploadedFile('support.pdf', b'%PDF-1.7\nsample'),
            uploaded_by=self.teacher,
        )
        draft_lesson = Lesson.objects.create(course=published_course, title='Non publiée', content='Secret')
        private_doc = Material.objects.create(
            course=published_course,
            lesson=draft_lesson,
            title='Document privé',
            file=SimpleUploadedFile('private.pdf', b'%PDF-1.7\nprivate'),
            uploaded_by=self.teacher,
        )
        Enrollment.objects.create(student=self.student, subject=self.subject)

        student_client = APIClient()
        student_client.force_authenticate(self.student)
        lessons = student_client.get(f'/api/courses/{course.pk}/lessons/')
        self.assertEqual(lessons.status_code, 404)

        course_response = student_client.get(f'/api/courses/{published_course.pk}/')
        self.assertEqual(course_response.status_code, 200)
        self.assertEqual(course_response.data['lessons'], [])
        self.assertEqual([item['id'] for item in course_response.data['materials']], [published_doc.pk])
        self.assertNotIn(private_doc.pk, [item['id'] for item in course_response.data['materials']])
        self.assertEqual(student_client.get(f'/api/materials/{private_doc.pk}/download/').status_code, 404)

        published_lesson.course = published_course
        published_lesson.save()
        self.assertEqual(student_client.get(f'/api/lessons/{published_lesson.pk}/').status_code, 200)

    def test_professor_cannot_change_subject_assignments_or_enrollments(self):
        subject_update = self.client.patch(f'/api/subjects/{self.subject.pk}/', {'teacher': self.other_teacher.pk}, format='json')
        self.assertEqual(subject_update.status_code, 403)
        enrollment_write = self.client.post('/api/enrollments/', {'student': self.student.pk, 'subject': self.subject.pk}, format='json')
        self.assertEqual(enrollment_write.status_code, 403)
        self.assertEqual(self.client.get('/api/enrollments/').status_code, 200)

    def test_assignment_submission_and_grading_are_scoped(self):
        course = self.make_course()
        assignment_response = self.client.post('/api/assignments/', {
            'course': course.pk,
            'title': 'Devoir 1',
            'instructions': 'Résoudre les exercices',
            'is_published': True,
        }, format='json')
        self.assertEqual(assignment_response.status_code, 201)
        assignment_id = assignment_response.data['id']
        Enrollment.objects.create(student=self.student, subject=self.subject)

        student_client = APIClient()
        student_client.force_authenticate(self.student)
        self.assertEqual(student_client.get('/api/student/graded-submissions/').data, [])
        self.assertEqual(self.client.get('/api/student/graded-submissions/').status_code, 403)
        submission_response = student_client.post(
            f'/api/assignments/{assignment_id}/submissions/',
            {'file': SimpleUploadedFile('travail.pdf', b'%PDF-1.7\nsubmission'), 'comment': 'Travail rendu'},
            format='multipart',
        )
        self.assertEqual(submission_response.status_code, 201)
        submission = Submission.objects.get(pk=submission_response.data['id'])
        teacher_submissions = self.client.get(f'/api/assignments/{assignment_id}/submissions/')
        self.assertEqual(teacher_submissions.status_code, 200)
        self.assertTrue(teacher_submissions.data[0]['file_name'].endswith('.pdf'))
        self.assertTrue(teacher_submissions.data[0]['file_url'].endswith(f'/api/submissions/{submission.pk}/download/'))
        file_response = self.client.get(f'/api/submissions/{submission.pk}/download/')
        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', file_response['Content-Disposition'])
        grade_response = self.client.patch(
            f'/api/submissions/{submission.pk}/',
            {
                'grade': '17.50',
                'feedback': 'Bon travail',
                'corrected_file': SimpleUploadedFile('corrige.pdf', b'%PDF-1.7\ncorrected'),
            },
            format='multipart',
        )
        self.assertEqual(grade_response.status_code, 200)
        self.assertTrue(grade_response.data['corrected_file_url'].endswith(
            f'/api/submissions/{submission.pk}/corrected-download/',
        ))
        self.assertTrue(grade_response.data['corrected_file_name'].endswith('.pdf'))
        corrected_download = student_client.get(f'/api/submissions/{submission.pk}/corrected-download/')
        self.assertEqual(corrected_download.status_code, 200)
        self.assertEqual(corrected_download['Content-Type'], 'application/pdf')
        submission.refresh_from_db()
        self.assertEqual(str(submission.grade), '17.50')
        self.assertIsNotNone(submission.graded_at)
        grades_response = student_client.get('/api/student/graded-submissions/')
        self.assertEqual(grades_response.status_code, 200)
        self.assertEqual(len(grades_response.data), 1)
        self.assertEqual(grades_response.data[0]['id'], submission.pk)
        self.assertEqual(grades_response.data[0]['grade'], '17.50')
        self.assertEqual(grades_response.data[0]['feedback'], 'Bon travail')
        self.assertEqual(grades_response.data[0]['assignment_title'], 'Devoir 1')
        self.assertEqual(grades_response.data[0]['course_title'], course.title)
        self.assertTrue(grades_response.data[0]['corrected_file_url'])

        other_student = User.objects.create_user(
            email='another-student@test.local',
            password='OtherStudentPass123!',
            role='student',
        )
        Submission.objects.create(
            assignment=submission.assignment,
            student=other_student,
            file=SimpleUploadedFile('autre-travail.pdf', b'%PDF-1.7\nother'),
            grade='12.00',
            graded_at=timezone.now(),
        )
        self.assertEqual(
            [item['id'] for item in student_client.get('/api/student/graded-submissions/').data],
            [submission.pk],
        )
        other_student_client = APIClient()
        other_student_client.force_authenticate(other_student)
        self.assertEqual(
            other_student_client.get(f'/api/submissions/{submission.pk}/corrected-download/').status_code,
            404,
        )

        resubmit = student_client.post(
            f'/api/assignments/{assignment_id}/submissions/',
            {'file': SimpleUploadedFile('nouveau.pdf', b'%PDF-1.7\nnew')},
            format='multipart',
        )
        self.assertEqual(resubmit.status_code, 400)

    def test_assigned_subject_teacher_can_review_submissions_for_admin_owned_course(self):
        admin = User.objects.create_superuser(
            email='content-admin@test.local',
            password='AdminPass123!',
            first_name='Content',
            last_name='Admin',
        )
        course = self.make_course(teacher=admin, subject=self.subject)
        assignment = Assignment.objects.create(
            course=course,
            title='Devoir de matière attribuée',
            instructions='Travail à remettre.',
            is_published=True,
        )
        submission = Submission.objects.create(
            assignment=assignment,
            student=self.student,
            file=SimpleUploadedFile('travail.pdf', b'%PDF-1.7\nsubmission'),
        )

        courses = self.client.get('/api/courses/')
        self.assertEqual(courses.status_code, 200)
        self.assertIn(course.pk, [item['id'] for item in courses.data])

        assignments = self.client.get('/api/assignments/')
        self.assertEqual(assignments.status_code, 200)
        self.assertIn(assignment.pk, [item['id'] for item in assignments.data])

        submissions = self.client.get(f'/api/assignments/{assignment.pk}/submissions/')
        self.assertEqual(submissions.status_code, 200)
        self.assertEqual([item['id'] for item in submissions.data], [submission.pk])

        download = self.client.get(f'/api/submissions/{submission.pk}/download/')
        self.assertEqual(download.status_code, 200)
        self.assertTrue(submissions.data[0]['file_name'].endswith('.pdf'))
        self.assertEqual(download['Content-Type'], 'application/pdf')

        grade = self.client.patch(
            f'/api/submissions/{submission.pk}/',
            {'grade': '18.00', 'feedback': 'Bon travail.'},
            format='json',
        )
        self.assertEqual(grade.status_code, 200)

        other_teacher_client = APIClient()
        other_teacher_client.force_authenticate(self.other_teacher)
        self.assertNotIn(course.pk, [item['id'] for item in other_teacher_client.get('/api/courses/').data])
        self.assertEqual(
            other_teacher_client.get(f'/api/assignments/{assignment.pk}/submissions/').status_code,
            404,
        )
        self.assertEqual(other_teacher_client.get(f'/api/submissions/{submission.pk}/download/').status_code, 404)

    def test_only_course_teacher_can_retrieve_its_documents_and_submissions(self):
        course = self.make_course(teacher=self.other_teacher, subject=self.other_subject)
        material = Material.objects.create(
            course=course,
            title='Privé',
            file=SimpleUploadedFile('private.pdf', b'%PDF-1.7\nprivate'),
            uploaded_by=self.other_teacher,
        )
        self.assertEqual(self.client.get(f'/api/materials/{material.pk}/download/').status_code, 404)
        self.assertEqual(self.client.delete(f'/api/courses/{course.pk}/').status_code, 404)

    def test_teacher_password_change_checks_current_password(self):
        bad = self.client.post('/api/teacher/change-password/', {
            'current_password': 'incorrect',
            'new_password': 'NewTeacherPass123!',
        }, format='json')
        self.assertEqual(bad.status_code, 400)
        good = self.client.post('/api/teacher/change-password/', {
            'current_password': 'TeacherPass123!',
            'new_password': 'NewTeacherPass123!',
        }, format='json')
        self.assertEqual(good.status_code, 200)
        self.teacher.refresh_from_db()
        self.assertTrue(self.teacher.check_password('NewTeacherPass123!'))

    def test_student_dashboard_and_subjects_only_include_active_published_content(self):
        course = self.make_course()
        Lesson.objects.create(course=course, title='Leçon publiée', content='Contenu', status=Lesson.Status.PUBLISHED)
        Lesson.objects.create(course=course, title='Leçon brouillon', content='Privé')
        Material.objects.create(
            course=course,
            title='Support',
            file=SimpleUploadedFile('support.pdf', b'%PDF-1.7\nsample'),
            uploaded_by=self.teacher,
        )
        Assignment.objects.create(course=course, title='Devoir publié', instructions='Consignes', is_published=True)
        inactive_course = self.make_course(subject=self.other_subject)
        Lesson.objects.create(course=inactive_course, title='Autre matière', content='Inaccessible', status=Lesson.Status.PUBLISHED)
        Enrollment.objects.create(student=self.student, subject=self.subject)

        student_client = APIClient()
        student_client.force_authenticate(self.student)
        dashboard = student_client.get('/api/student/dashboard/')
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.data['subject_count'], 1)
        self.assertEqual(dashboard.data['course_count'], 1)
        self.assertEqual(dashboard.data['lesson_count'], 1)
        self.assertEqual(dashboard.data['material_count'], 1)
        self.assertEqual(dashboard.data['pending_assignment_count'], 1)

        subjects = student_client.get('/api/student/subjects/?search=INFO')
        self.assertEqual(subjects.status_code, 200)
        self.assertEqual([item['id'] for item in subjects.data], [self.subject.pk])
        self.assertEqual(subjects.data[0]['course_count'], 1)
        self.assertEqual(self.client.get('/api/student/dashboard/').status_code, 403)

    def test_teacher_publishes_announcement_and_students_only_see_accessible_publications(self):
        course_response = self.client.post('/api/courses/', {
            'title': 'Cours avec annonces',
            'description': 'Cours publié pour les étudiants inscrits.',
            'subject': self.subject.pk,
            'status': Course.Status.PUBLISHED,
        }, format='json')
        self.assertEqual(course_response.status_code, 201, course_response.data)
        course_id = course_response.data['id']

        published_lesson = self.client.post(f'/api/courses/{course_id}/lessons/', {
            'title': 'Leçon publiée',
            'content': 'Contenu visible.',
            'status': Lesson.Status.PUBLISHED,
        }, format='json')
        self.assertEqual(published_lesson.status_code, 201, published_lesson.data)
        draft_lesson = self.client.post(f'/api/courses/{course_id}/lessons/', {
            'title': 'Leçon privée',
            'content': 'Contenu non publié.',
        }, format='json')
        self.assertEqual(draft_lesson.status_code, 201, draft_lesson.data)

        assignment = self.client.post('/api/assignments/', {
            'course': course_id,
            'title': 'Devoir publié',
            'instructions': 'Réalisez le travail.',
            'is_published': True,
        }, format='json')
        self.assertEqual(assignment.status_code, 201, assignment.data)
        draft_assignment = self.client.post('/api/assignments/', {
            'course': course_id,
            'title': 'Devoir en brouillon',
            'instructions': 'Ces consignes ne sont pas encore publiques.',
            'is_published': False,
        }, format='json')
        self.assertEqual(draft_assignment.status_code, 201, draft_assignment.data)
        published_announcement = self.client.post('/api/announcements/', {
            'course': course_id,
            'title': 'Information de cours',
            'content': 'La séance aura lieu en salle 2.',
            'status': Announcement.Status.PUBLISHED,
        }, format='json')
        self.assertEqual(published_announcement.status_code, 201, published_announcement.data)
        self.assertEqual(published_announcement.data['teacher_id'], self.teacher.pk)
        self.assertIsNotNone(published_announcement.data['published_at'])
        draft_announcement = self.client.post('/api/announcements/', {
            'course': course_id,
            'title': 'Information en brouillon',
            'content': 'Cette information n’est pas encore publique.',
        }, format='json')
        self.assertEqual(draft_announcement.status_code, 201, draft_announcement.data)

        Enrollment.objects.create(student=self.student, subject=self.subject)
        student_client = APIClient()
        student_client.force_authenticate(self.student)
        student_courses = student_client.get('/api/courses/')
        self.assertEqual(student_courses.status_code, 200)
        visible_course = next(item for item in student_courses.data if item['id'] == course_id)
        self.assertEqual([item['id'] for item in visible_course['lessons']], [published_lesson.data['id']])
        self.assertEqual([item['id'] for item in visible_course['assignments']], [assignment.data['id']])
        self.assertEqual([item['id'] for item in visible_course['announcements']], [published_announcement.data['id']])
        self.assertEqual(
            [item['id'] for item in student_client.get('/api/assignments/').data],
            [assignment.data['id']],
        )
        self.assertEqual(
            student_client.get(f"/api/assignments/{draft_assignment.data['id']}/").status_code,
            404,
        )
        self.assertEqual(
            [item['id'] for item in student_client.get('/api/announcements/').data],
            [published_announcement.data['id']],
        )
        self.assertEqual(
            student_client.get(f"/api/announcements/{draft_announcement.data['id']}/").status_code,
            404,
        )

        outsider = User.objects.create_user(
            email='announcement-outsider@test.local',
            password='OutsiderPass123!',
            first_name='Other',
            last_name='Student',
            role='student',
        )
        outsider_client = APIClient()
        outsider_client.force_authenticate(outsider)
        self.assertEqual(outsider_client.get('/api/announcements/').data, [])
        self.assertEqual(
            outsider_client.get(f"/api/announcements/{published_announcement.data['id']}/").status_code,
            404,
        )

        admin = User.objects.create_superuser(
            email='announcement-admin@test.local',
            password='AdminPass123!',
            first_name='Admin',
            last_name='Announcement',
        )
        admin_client = APIClient()
        admin_client.force_authenticate(admin)
        admin_courses = admin_client.get('/api/courses/')
        self.assertIn(course_id, [item['id'] for item in admin_courses.data])
        admin_course = next(item for item in admin_courses.data if item['id'] == course_id)
        self.assertEqual(
            {item['id'] for item in admin_course['lessons']},
            {published_lesson.data['id'], draft_lesson.data['id']},
        )
        admin_assignments = admin_client.get('/api/assignments/')
        self.assertEqual(len(admin_assignments.data), 2)
        admin_announcements = admin_client.get('/api/announcements/')
        self.assertEqual(admin_announcements.status_code, 200)
        self.assertEqual(len(admin_announcements.data), 2)
        self.assertEqual(admin_announcements.data[0]['course_title'], 'Cours avec annonces')

    def test_teacher_sees_admin_announcement_changes_for_assigned_subject(self):
        admin = User.objects.create_superuser(
            email='announcement-moderator@test.local',
            password='AdminPass123!',
            first_name='Amina',
            last_name='Admin',
        )
        admin_course = self.make_course(teacher=admin, subject=self.subject)
        announcement = Announcement.objects.create(
            course=admin_course,
            title='Information initiale',
            content='Texte initial.',
            status=Announcement.Status.PUBLISHED,
        )
        admin_client = APIClient()
        admin_client.force_authenticate(admin)
        update = admin_client.patch(
            f'/api/announcements/{announcement.pk}/',
            {
                'title': 'Information mise à jour',
                'content': 'Le contenu modifié par l’administration.',
                'status': Announcement.Status.DRAFT,
            },
            format='json',
        )
        self.assertEqual(update.status_code, 200)

        announcements = self.client.get('/api/announcements/')
        self.assertEqual(announcements.status_code, 200)
        self.assertEqual(len(announcements.data), 1)
        visible_announcement = announcements.data[0]
        self.assertEqual(visible_announcement['id'], announcement.pk)
        self.assertEqual(visible_announcement['title'], 'Information mise à jour')
        self.assertEqual(visible_announcement['content'], 'Le contenu modifié par l’administration.')
        self.assertEqual(visible_announcement['status'], Announcement.Status.DRAFT)
        self.assertEqual(visible_announcement['modified_by_name'], 'Amina Admin')
        self.assertEqual(visible_announcement['modified_by_role'], 'admin')
        self.assertIsNotNone(visible_announcement['updated_at'])

        self.assertEqual(
            self.client.patch(
                f'/api/announcements/{announcement.pk}/',
                {'title': 'Modification non autorisée'},
                format='json',
            ).status_code,
            403,
        )
        self.assertEqual(self.client.delete(f'/api/announcements/{announcement.pk}/').status_code, 403)
        self.assertEqual(
            self.client.get(f'/api/announcements/{announcement.pk}/').data['content'],
            'Le contenu modifié par l’administration.',
        )

    def test_student_progress_is_owned_and_only_for_accessible_published_lessons(self):
        course = self.make_course()
        lesson = Lesson.objects.create(course=course, title='Leçon', content='Contenu', status=Lesson.Status.PUBLISHED)
        draft = Lesson.objects.create(course=course, title='Brouillon', content='Secret')
        Enrollment.objects.create(student=self.student, subject=self.subject)
        student_client = APIClient()
        student_client.force_authenticate(self.student)

        marked = student_client.post(f'/api/student/lessons/{lesson.pk}/progress/', {'completed': True}, format='json')
        self.assertEqual(marked.status_code, 200)
        self.assertTrue(marked.data['completed'])
        self.assertEqual(LessonProgress.objects.filter(student=self.student, lesson=lesson).count(), 1)
        listed = student_client.get('/api/student/progress/')
        self.assertEqual([item['lesson'] for item in listed.data], [lesson.pk])
        self.assertEqual(student_client.post(f'/api/student/lessons/{draft.pk}/progress/', {'completed': True}, format='json').status_code, 404)

        other_student = User.objects.create_user(
            email='other-student@test.local',
            password='OtherStudentPass123!',
            first_name='Alex',
            last_name='Other',
            role='student',
        )
        other_client = APIClient()
        other_client.force_authenticate(other_student)
        self.assertEqual(other_client.get(f'/api/student/lessons/{lesson.pk}/progress/').status_code, 404)
        self.assertEqual(other_client.get('/api/student/progress/').data, [])

    def test_student_profile_cannot_change_role_or_admin_managed_fields(self):
        student_client = APIClient()
        student_client.force_authenticate(self.student)
        response = student_client.patch('/api/student/profile/', {
            'first_name': 'Sammy',
            'email': 'sammy@test.local',
            'role': 'admin',
            'matricule': 'ADMIN-1',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.student.refresh_from_db()
        self.assertEqual(self.student.first_name, 'Sammy')
        self.assertEqual(self.student.email, 'sammy@test.local')
        self.assertEqual(self.student.role, 'student')
        self.assertNotEqual(self.student.matricule, 'ADMIN-1')

        bad_password = student_client.post('/api/student/change-password/', {
            'current_password': 'incorrect',
            'new_password': 'StudentNewPass123!',
        }, format='json')
        self.assertEqual(bad_password.status_code, 400)
        changed = student_client.post('/api/student/change-password/', {
            'current_password': 'StudentPass123!',
            'new_password': 'StudentNewPass123!',
        }, format='json')
        self.assertEqual(changed.status_code, 200)
        self.student.refresh_from_db()
        self.assertTrue(self.student.check_password('StudentNewPass123!'))
        self.assertEqual(self.client.get('/api/student/profile/').status_code, 403)


class SocialFeedTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='admin-feed@test.local',
            password='AdminPass123!',
            first_name='Amina',
            last_name='Admin',
        )
        self.teacher = User.objects.create_user(
            email='teacher-feed@test.local',
            password='TeacherPass123!',
            first_name='Tessa',
            last_name='Teacher',
            role='teacher',
        )
        self.student = User.objects.create_user(
            email='student-feed@test.local',
            password='StudentPass123!',
            first_name='Sam',
            last_name='Student',
            role='student',
        )
        self.faculty = Faculty.objects.create(name='Sciences', code='SCI')
        self.level = AcademicLevel.objects.create(name='Licence 1', code='L1', faculty=self.faculty)
        self.year = AcademicYear.objects.create(
            name='2026-2027-feed',
            start_date='2026-09-01',
            end_date='2027-06-30',
        )
        self.subject = Subject.objects.create(
            code='SCI101',
            name='Sciences générales',
            faculty=self.faculty,
            level=self.level,
            academic_year=self.year,
            teacher=self.teacher,
        )
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        self.teacher_client = APIClient()
        self.teacher_client.force_authenticate(self.teacher)
        self.student_client = APIClient()
        self.student_client.force_authenticate(self.student)

    def test_admin_posts_are_shared_and_teacher_student_can_like_and_comment(self):
        created = self.admin_client.post('/api/social-posts/', {
            'title': 'Information importante',
            'content': 'La rentrée aura lieu lundi.',
        }, format='json')
        self.assertEqual(created.status_code, 201, created.data)
        post_id = created.data['id']
        self.assertEqual(created.data['author_name'], 'Amina Admin')
        self.assertEqual(self.teacher_client.get('/api/social-posts/').data[0]['id'], post_id)
        self.assertEqual(self.student_client.get('/api/social-posts/').data[0]['id'], post_id)

        liked = self.teacher_client.post(f'/api/social-posts/{post_id}/like/')
        self.assertEqual(liked.status_code, 200)
        self.assertTrue(liked.data['liked_by_me'])
        self.assertEqual(liked.data['like_count'], 1)
        unliked = self.teacher_client.post(f'/api/social-posts/{post_id}/like/')
        self.assertFalse(unliked.data['liked_by_me'])
        self.assertEqual(unliked.data['like_count'], 0)

        comment = self.student_client.post(
            f'/api/social-posts/{post_id}/comments/',
            {'content': 'Merci pour cette information.'},
            format='json',
        )
        self.assertEqual(comment.status_code, 201, comment.data)
        self.assertEqual(comment.data['author_name'], 'Sam Student')
        feed_post = self.teacher_client.get('/api/social-posts/').data[0]
        self.assertEqual(feed_post['comments'][0]['content'], 'Merci pour cette information.')

        teacher_post = self.teacher_client.post('/api/social-posts/', {
            'title': 'Information du professeur',
            'content': 'Cette annonce est partagée avec tous les utilisateurs.',
        }, format='json')
        self.assertEqual(teacher_post.status_code, 201, teacher_post.data)
        self.assertEqual(teacher_post.data['kind'], SocialPost.Kind.TEACHER)
        self.assertEqual(teacher_post.data['author_name'], 'Tessa Teacher')
        self.assertEqual(self.student_client.get('/api/social-posts/').data[0]['id'], teacher_post.data['id'])
        self.assertEqual(self.admin_client.get('/api/social-posts/').data[0]['id'], teacher_post.data['id'])
        self.assertEqual(self.student_client.post('/api/social-posts/', {
            'title': 'Publication non autorisée',
            'content': 'Contenu',
        }, format='json').status_code, 403)
        self.assertEqual(self.admin_client.post(f'/api/social-posts/{post_id}/like/').status_code, 403)
        self.assertEqual(self.admin_client.post(f'/api/social-posts/{post_id}/comments/', {
            'content': 'Commentaire admin',
        }, format='json').status_code, 403)

    def test_only_admin_can_reply_to_a_top_level_post_comment(self):
        created = self.admin_client.post('/api/social-posts/', {
            'title': 'Information importante',
            'content': 'La rentrée aura lieu lundi.',
        }, format='json')
        post_id = created.data['id']
        comment = self.student_client.post(
            f'/api/social-posts/{post_id}/comments/',
            {'content': 'À quelle heure ?'},
            format='json',
        )
        comment_id = comment.data['id']
        reply_url = f'/api/social-posts/{post_id}/comments/{comment_id}/replies/'
        reply_payload = {'content': 'À 9 heures.'}

        reply = self.admin_client.post(reply_url, reply_payload, format='json')
        self.assertEqual(reply.status_code, 201, reply.data)
        self.assertEqual(reply.data['author_role'], 'admin')
        self.assertEqual(reply.data['content'], reply_payload['content'])
        feed_comment = self.student_client.get('/api/social-posts/').data[0]['comments'][0]
        self.assertEqual(feed_comment['replies'][0]['id'], reply.data['id'])

        self.assertEqual(self.teacher_client.post(reply_url, reply_payload, format='json').status_code, 403)
        self.assertEqual(self.student_client.post(reply_url, reply_payload, format='json').status_code, 403)
        nested_reply_url = f'/api/social-posts/{post_id}/comments/{reply.data["id"]}/replies/'
        self.assertEqual(self.admin_client.post(nested_reply_url, reply_payload, format='json').status_code, 404)

    def test_teacher_assignment_reference_file_is_downloadable_by_enrolled_student(self):
        course = Course.objects.create(
            title='Cours partagé',
            slug='cours-partage-feed',
            description='Description',
            subject=self.subject,
            teacher=self.teacher,
            status=Course.Status.PUBLISHED,
        )
        Enrollment.objects.create(student=self.student, subject=self.subject)
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            assignment = Assignment.objects.create(
                course=course,
                title='Document de travail',
                instructions='Consultez le document.',
                reference_file=SimpleUploadedFile('consignes.pdf', b'%PDF-1.7\ncontenu de test'),
                is_published=True,
            )

            response = self.student_client.get(f'/api/assignments/{assignment.pk}/')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['reference_file_name'], 'consignes.pdf')
            self.assertTrue(response.data['reference_file_url'])
            download = self.student_client.get(f'/api/assignments/{assignment.pk}/reference/')
            self.assertEqual(download.status_code, 200)
            self.assertIn('attachment', download['Content-Disposition'])
            self.assertEqual(b''.join(download.streaming_content), b'%PDF-1.7\ncontenu de test')

    def test_admin_can_publish_validated_image_with_a_social_post(self):
        image_buffer = BytesIO()
        Image.new('RGB', (8, 8), color='blue').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        uploaded_image = SimpleUploadedFile('actualite.png', image_buffer.read(), content_type='image/png')

        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            created = self.admin_client.post('/api/social-posts/', {
                'title': 'Photo de la rentrée',
                'content': 'Les préparatifs sont en cours.',
                'image': uploaded_image,
            }, format='multipart')
            self.assertEqual(created.status_code, 201, created.data)
            self.assertTrue(created.data['image_url'])

            post_id = created.data['id']
            image_response = self.student_client.get(created.data['image_url'])
            self.assertEqual(image_response.status_code, 200)
            self.assertEqual(image_response['Content-Type'], 'image/png')
            self.assertIn('inline', image_response['Content-Disposition'])
            self.assertEqual(b''.join(image_response.streaming_content), image_buffer.getvalue())

            invalid_upload = SimpleUploadedFile(
                'pas-une-image.png',
                b'text not an image',
                content_type='image/png',
            )
            invalid_response = self.admin_client.post('/api/social-posts/', {
                'title': 'Fichier invalide',
                'content': 'Ce fichier doit être refusé.',
                'image': invalid_upload,
            }, format='multipart')
            self.assertEqual(invalid_response.status_code, 400)
            self.assertIn('image', invalid_response.data)

    def test_admin_can_publish_mp4_video_and_students_can_view_it(self):
        video_bytes = b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00'
        uploaded_video = SimpleUploadedFile(
            'annonce.mp4',
            video_bytes,
            content_type='video/mp4',
        )
        with TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            created = self.admin_client.post('/api/social-posts/', {
                'title': 'Vidéo de présentation',
                'content': 'Découvrez notre université.',
                'video': uploaded_video,
            }, format='multipart')
            self.assertEqual(created.status_code, 201, created.data)
            self.assertTrue(created.data['video_url'])
            self.assertEqual(created.data['image_url'], '')

            video_response = self.student_client.get(created.data['video_url'])
            self.assertEqual(video_response.status_code, 200)
            self.assertEqual(video_response['Content-Type'], 'video/mp4')
            self.assertIn('inline', video_response['Content-Disposition'])
            self.assertEqual(b''.join(video_response.streaming_content), video_bytes)

            invalid_video = SimpleUploadedFile(
                'document.mp4',
                b'this is not an mp4',
                content_type='video/mp4',
            )
            invalid_response = self.admin_client.post('/api/social-posts/', {
                'title': 'Vidéo invalide',
                'content': 'Le fichier doit être refusé.',
                'video': invalid_video,
            }, format='multipart')
            self.assertEqual(invalid_response.status_code, 400)
            self.assertIn('video', invalid_response.data)

    def test_social_feed_with_uploaded_media_can_be_listed(self):
        image_buffer = BytesIO()
        Image.new('RGB', (8, 8), color='green').save(image_buffer, format='PNG')
        image_buffer.seek(0)
        created = self.admin_client.post('/api/social-posts/', {
            'title': 'Publication avec image',
            'content': 'Texte de test',
            'image': SimpleUploadedFile('feed.png', image_buffer.read(), content_type='image/png'),
        }, format='multipart')
        self.assertEqual(created.status_code, 201, created.data)

        response = self.student_client.get('/api/social-posts/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['id'], created.data['id'])
        self.assertEqual(response.data[0]['image_url'], created.data['image_url'])
        self.assertEqual(response.data[0]['video_url'], '')
        self.assertTrue(response.data[0]['image_url'].startswith('/api/'))

    def test_admin_course_and_subject_changes_are_published_to_the_feed(self):
        subject_response = self.admin_client.post('/api/subjects/', {
            'code': 'SCI202',
            'name': 'Physique appliquée',
            'description': 'Notions fondamentales',
            'faculty': self.faculty.pk,
            'level': self.level.pk,
            'academic_year': self.year.pk,
            'teacher': self.teacher.pk,
        }, format='json')
        self.assertEqual(subject_response.status_code, 201, subject_response.data)
        subject_id = subject_response.data['id']
        subject_post = SocialPost.objects.get(subject_id=subject_id, kind=SocialPost.Kind.SUBJECT)
        self.assertIn('Nouvelle matière', subject_post.title)

        subject_update = self.admin_client.patch(
            f'/api/subjects/{subject_id}/',
            {'name': 'Physique moderne'},
            format='json',
        )
        self.assertEqual(subject_update.status_code, 200, subject_update.data)
        self.assertEqual(
            SocialPost.objects.filter(subject_id=subject_id, kind=SocialPost.Kind.SUBJECT).count(),
            2,
        )

        course_response = self.admin_client.post('/api/courses/', {
            'title': 'Mécanique',
            'description': 'Introduction aux mouvements',
            'subject': subject_id,
            'status': Course.Status.PUBLISHED,
        }, format='json')
        self.assertEqual(course_response.status_code, 201, course_response.data)
        course_id = course_response.data['id']
        self.assertTrue(SocialPost.objects.filter(course_id=course_id, kind=SocialPost.Kind.COURSE).exists())

        course_update = self.admin_client.patch(
            f'/api/courses/{course_id}/',
            {'title': 'Mécanique générale'},
            format='json',
        )
        self.assertEqual(course_update.status_code, 200, course_update.data)
        self.assertEqual(
            SocialPost.objects.filter(course_id=course_id, kind=SocialPost.Kind.COURSE).count(),
            2,
        )
