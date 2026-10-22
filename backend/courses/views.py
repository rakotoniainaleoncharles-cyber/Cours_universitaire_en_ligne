import os

from django.contrib.auth import get_user_model, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.db.models import Count, Q
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from academics.models import Subject
from academics.serializers import SubjectSerializer
from accounts.audit import log_admin_action
from users.models import Enrollment

from .models import (
    Announcement,
    Assignment,
    Course,
    Lesson,
    LessonProgress,
    Material,
    SocialPost,
    SocialPostComment,
    SocialPostLike,
    Submission,
)
from .serializers import (
    AnnouncementSerializer,
    AssignmentSerializer,
    CourseSerializer,
    LessonSerializer,
    MaterialSerializer,
    SocialPostCommentSerializer,
    SocialPostCreateSerializer,
    SocialPostSerializer,
    SubmissionSerializer,
)
from .social import create_admin_activity_post

User = get_user_model()


def teacher_courses(user):
    return Course.objects.filter(Q(teacher=user) | Q(subject__teacher=user))


def is_course_assigned_to_teacher(user, course):
    return course.teacher_id == user.id or course.subject.teacher_id == user.id


def visible_courses(user):
    courses = Course.objects.select_related('subject', 'subject__faculty', 'subject__level', 'teacher').prefetch_related(
        'lessons', 'materials', 'assignments',
    )
    if user.is_admin:
        return courses
    if user.is_teacher:
        return courses.filter(Q(teacher=user) | Q(subject__teacher=user)).distinct()
    return courses.filter(
        subject__enrollments__student=user,
        subject__enrollments__status=Enrollment.Status.ACTIVE,
        status=Course.Status.PUBLISHED,
    ).distinct()


def can_access_course(user, course):
    if user.is_admin or course.teacher_id == user.id:
        return True
    return user.is_student and course.status == Course.Status.PUBLISHED and Enrollment.objects.filter(
        student=user,
        subject=course.subject,
        status=Enrollment.Status.ACTIVE,
    ).exists()


def accessible_materials(user):
    materials = Material.objects.select_related('course', 'lesson', 'uploaded_by')
    if user.is_admin:
        return materials
    if user.is_teacher:
        return materials.filter(course__teacher=user)
    return materials.filter(
        course__subject__enrollments__student=user,
        course__subject__enrollments__status=Enrollment.Status.ACTIVE,
        course__status=Course.Status.PUBLISHED,
    ).filter(Q(lesson__isnull=True) | Q(lesson__status=Lesson.Status.PUBLISHED)).distinct()


class TeacherOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_teacher)


class StudentOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)


class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = visible_courses(self.request.user)
        search = self.request.query_params.get('search', '').strip()
        status_filter = self.request.query_params.get('status')
        subject_id = self.request.query_params.get('subject')
        ordering = self.request.query_params.get('ordering', '-created_at')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
        if status_filter in Course.Status.values:
            queryset = queryset.filter(status=status_filter)
        if subject_id:
            queryset = queryset.filter(subject_id=subject_id)
        if ordering in {'title', '-title', 'created_at', '-created_at', 'updated_at', '-updated_at'}:
            queryset = queryset.order_by(ordering)
        return queryset

    def perform_create(self, serializer):
        if not (self.request.user.is_admin or self.request.user.is_teacher):
            self.permission_denied(self.request, message='Vous ne pouvez pas créer de cours.')
        course = serializer.save(teacher=self.request.user)
        if self.request.user.is_admin:
            create_admin_activity_post(
                self.request.user,
                SocialPost.Kind.COURSE,
                f'Nouveau cours : {course.title}',
                f'L’administration a ajouté le cours « {course.title} » dans la matière « {course.subject.name} ».',
                course=course,
                subject=course.subject,
            )


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return visible_courses(self.request.user)

    def update(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas modifier ce cours.')
        course = self.get_object()
        previous = {
            'title': course.title,
            'description': course.description,
            'objectives': course.objectives,
            'subject_id': course.subject_id,
            'teacher_id': course.teacher_id,
            'status': course.status,
        }
        if request.user.is_admin:
            log_admin_action(request.user, 'update', 'Course', course.pk, f'Modération du cours {course.title}')
        response = super().update(request, *args, **kwargs)
        if request.user.is_admin:
            course.refresh_from_db()
            changed_fields = [
                field for field, value in previous.items()
                if getattr(course, field) != value
            ]
            if changed_fields:
                labels = {
                    'title': 'titre',
                    'description': 'description',
                    'objectives': 'objectifs',
                    'subject_id': 'matière',
                    'teacher_id': 'professeur responsable',
                    'status': 'statut de publication',
                }
                create_admin_activity_post(
                    request.user,
                    SocialPost.Kind.COURSE,
                    f'Mise à jour du cours : {course.title}',
                    f'L’administration a modifié le cours « {course.title} » ({", ".join(labels[field] for field in changed_fields)}).',
                    course=course,
                    subject=course.subject,
                )
        return response

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas supprimer ce cours.')
        course = self.get_object()
        if request.user.is_admin:
            log_admin_action(request.user, 'delete', 'Course', course.pk, f'Suppression du cours {course.title}')
            create_admin_activity_post(
                request.user,
                SocialPost.Kind.COURSE,
                f'Suppression du cours : {course.title}',
                f'L’administration a supprimé le cours « {course.title} » de la matière « {course.subject.name} ».',
                subject=course.subject,
            )
        return super().destroy(request, *args, **kwargs)


class AnnouncementListCreateView(generics.ListCreateAPIView):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Announcement.objects.select_related(
            'course', 'course__teacher', 'course__subject__faculty',
        )
        if user.is_admin:
            return queryset
        if user.is_teacher:
            return queryset.filter(course__in=teacher_courses(user)).select_related('modified_by')
        return queryset.filter(
            course__subject__enrollments__student=user,
            course__subject__enrollments__status=Enrollment.Status.ACTIVE,
            course__status=Course.Status.PUBLISHED,
            status=Announcement.Status.PUBLISHED,
        ).distinct()

    def create(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas créer une publication.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = get_object_or_404(visible_courses(request.user), pk=request.data.get('course'))
        if request.user.is_teacher and course.teacher_id != request.user.id:
            self.permission_denied(request, message='Ce cours ne vous appartient pas.')
        announcement = serializer.save(course=course, modified_by=request.user)
        if request.user.is_admin:
            log_admin_action(
                request.user, 'create', 'Announcement', announcement.pk,
                f'Création de la publication {announcement.title}',
            )
            if announcement.status == Announcement.Status.PUBLISHED:
                create_admin_activity_post(
                    request.user,
                    SocialPost.Kind.ADMIN,
                    announcement.title,
                    announcement.content,
                    course=announcement.course,
                    subject=announcement.course.subject,
                )
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AnnouncementDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Announcement.objects.select_related(
            'course', 'course__teacher', 'course__subject__faculty',
        )
        if user.is_admin:
            return queryset
        if user.is_teacher:
            return queryset.filter(course__in=teacher_courses(user)).select_related('modified_by')
        return queryset.filter(
            course__subject__enrollments__student=user,
            course__subject__enrollments__status=Enrollment.Status.ACTIVE,
            course__status=Course.Status.PUBLISHED,
            status=Announcement.Status.PUBLISHED,
        ).distinct()

    def update(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas modifier cette publication.')
        announcement = self.get_object()
        if request.user.is_teacher and announcement.course.teacher_id != request.user.id:
            self.permission_denied(request, message='Vous ne pouvez pas modifier cette publication.')
        previous = (announcement.title, announcement.content, announcement.status)
        response = super().update(request, *args, **kwargs)
        if request.user.is_admin:
            announcement.refresh_from_db()
            log_admin_action(
                request.user, 'update', 'Announcement', announcement.pk,
                f'Modération de la publication {announcement.title}',
            )
            if announcement.status == Announcement.Status.PUBLISHED and previous != (
                announcement.title, announcement.content, announcement.status,
            ):
                create_admin_activity_post(
                    request.user,
                    SocialPost.Kind.ADMIN,
                    announcement.title,
                    announcement.content,
                    course=announcement.course,
                    subject=announcement.course.subject,
                )
        return response

    def perform_update(self, serializer):
        serializer.save(modified_by=self.request.user)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas supprimer cette publication.')
        announcement = self.get_object()
        if request.user.is_teacher and announcement.course.teacher_id != request.user.id:
            self.permission_denied(request, message='Vous ne pouvez pas supprimer cette publication.')
        if request.user.is_admin:
            log_admin_action(
                request.user, 'delete', 'Announcement', announcement.pk,
                f'Suppression de la publication {announcement.title}',
            )
        return super().destroy(request, *args, **kwargs)


class SocialPostListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SocialPost.objects.select_related('author', 'course', 'subject').prefetch_related(
            'likes', 'comments__author', 'comments__replies__author',
        )

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return SocialPostCreateSerializer
        return SocialPostSerializer

    def create(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Seuls les professeurs et l’administration peuvent créer une publication générale.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        kind = SocialPost.Kind.ADMIN if request.user.is_admin else SocialPost.Kind.TEACHER
        post = serializer.save(author=request.user, kind=kind)
        return Response(
            SocialPostSerializer(post, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class SocialPostImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(SocialPost, pk=pk)
        if not post.image:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        image_file = post.image.open('rb')
        extension = os.path.splitext(post.image.name)[1].lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
        }.get(extension, 'application/octet-stream')
        response = FileResponse(
            image_file,
            content_type=content_type,
        )
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(post.image.name)}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class SocialPostVideoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        post = get_object_or_404(SocialPost, pk=pk)
        if not post.video:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        video_file = post.video.open('rb')
        extension = os.path.splitext(post.video.name)[1].lower()
        content_type = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
        }.get(extension, 'application/octet-stream')
        response = FileResponse(video_file, content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(post.video.name)}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class SocialPostLikeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not (request.user.is_teacher or request.user.is_student):
            self.permission_denied(request, message='Seuls les professeurs et les étudiants peuvent aimer une publication.')
        post = get_object_or_404(SocialPost, pk=pk)
        with transaction.atomic():
            like, created = SocialPostLike.objects.get_or_create(post=post, user=request.user)
            if not created:
                like.delete()
        post = SocialPost.objects.select_related('author', 'course', 'subject').prefetch_related(
            'likes', 'comments__author', 'comments__replies__author',
        ).get(pk=post.pk)
        return Response(SocialPostSerializer(post, context={'request': request}).data)


class SocialPostCommentCreateView(generics.CreateAPIView):
    serializer_class = SocialPostCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not (request.user.is_teacher or request.user.is_student):
            self.permission_denied(request, message='Seuls les professeurs et les étudiants peuvent commenter une publication.')
        post = get_object_or_404(SocialPost, pk=self.kwargs['pk'])
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = SocialPostComment.objects.create(
            post=post,
            author=request.user,
            content=serializer.validated_data['content'],
        )
        return Response(
            SocialPostCommentSerializer(comment, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class SocialPostCommentReplyCreateView(generics.CreateAPIView):
    serializer_class = SocialPostCommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        if not request.user.is_admin:
            self.permission_denied(request, message='Seule l’administration peut répondre aux commentaires.')
        post = get_object_or_404(SocialPost, pk=self.kwargs['pk'])
        parent_comment = get_object_or_404(
            SocialPostComment.objects.filter(post=post, parent_comment__isnull=True),
            pk=self.kwargs['comment_pk'],
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = SocialPostComment.objects.create(
            post=post,
            parent_comment=parent_comment,
            author=request.user,
            content=serializer.validated_data['content'],
        )
        return Response(
            SocialPostCommentSerializer(reply, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class LessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_course(self):
        return get_object_or_404(visible_courses(self.request.user), pk=self.kwargs['course_pk'])

    def get_queryset(self):
        course = self.get_course()
        queryset = Lesson.objects.filter(course=course)
        if self.request.user.is_student:
            queryset = queryset.filter(status=Lesson.Status.PUBLISHED)
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
        status_filter = self.request.query_params.get('status')
        if self.request.user.is_teacher and status_filter in Lesson.Status.values:
            queryset = queryset.filter(status=status_filter)
        return queryset.order_by('order', 'id')

    def create(self, request, *args, **kwargs):
        course = self.get_course()
        if not (request.user.is_admin or request.user == course.teacher):
            self.permission_denied(request, message='Vous ne pouvez pas ajouter une leçon à ce cours.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Lesson.objects.select_related('course', 'course__subject')
        if user.is_admin:
            return queryset
        if user.is_teacher:
            return queryset.filter(course__teacher=user)
        return queryset.filter(
            course__subject__enrollments__student=user,
            course__subject__enrollments__status=Enrollment.Status.ACTIVE,
            course__status=Course.Status.PUBLISHED,
            status=Lesson.Status.PUBLISHED,
        ).distinct()

    def update(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas modifier cette leçon.')
        lesson = self.get_object()
        if request.user.is_admin:
            log_admin_action(request.user, 'update', 'Lesson', lesson.pk, f'Modération de la leçon {lesson.title}')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas supprimer cette leçon.')
        lesson = self.get_object()
        if request.user.is_admin:
            log_admin_action(request.user, 'delete', 'Lesson', lesson.pk, f'Suppression de la leçon {lesson.title}')
        return super().destroy(request, *args, **kwargs)


class MaterialListCreateView(generics.ListCreateAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_course(self):
        return get_object_or_404(visible_courses(self.request.user), pk=self.kwargs['course_pk'])

    def get_queryset(self):
        course = self.get_course()
        queryset = accessible_materials(self.request.user).filter(course=course)
        if self.request.user.is_student:
            queryset = queryset.filter(Q(lesson__isnull=True) | Q(lesson__status=Lesson.Status.PUBLISHED))
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(description__icontains=search))
        return queryset.order_by('-uploaded_at')

    def create(self, request, *args, **kwargs):
        course = self.get_course()
        if not (request.user.is_admin or request.user == course.teacher):
            self.permission_denied(request, message='Vous ne pouvez pas téléverser un document pour ce cours.')
        serializer = self.get_serializer(data=request.data, context={**self.get_serializer_context(), 'course': course})
        serializer.is_valid(raise_exception=True)
        serializer.save(course=course, uploaded_by=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return accessible_materials(self.request.user)

    def update(self, request, *args, **kwargs):
        material = self.get_object()
        if not (request.user.is_admin or material.course.teacher_id == request.user.id):
            self.permission_denied(request, message='Vous ne pouvez pas modifier ce document.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        material = self.get_object()
        if not (request.user.is_admin or material.course.teacher_id == request.user.id):
            self.permission_denied(request, message='Vous ne pouvez pas supprimer ce document.')
        if request.user.is_admin:
            log_admin_action(request.user, 'delete', 'Material', material.pk, f'Suppression du document {material.title}')
        return super().destroy(request, *args, **kwargs)


class MaterialDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        material = get_object_or_404(accessible_materials(request.user), pk=pk)
        if request.user.is_student and material.lesson_id and material.lesson.status != Lesson.Status.PUBLISHED:
            return Response({'detail': 'Ce document n’est pas publié.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(material.file.open('rb'), as_attachment=True, filename=os.path.basename(material.file.name))


class CoursePublicListView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = visible_courses(self.request.user)
        if self.request.user.is_student:
            queryset = queryset.filter(status=Course.Status.PUBLISHED)
        return queryset


class TeacherDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, TeacherOnly]

    def get(self, request):
        subjects = Subject.objects.filter(teacher=request.user).select_related(
            'faculty', 'level', 'academic_year',
        )
        courses = teacher_courses(request.user).select_related('subject').prefetch_related('lessons')
        subject_ids = subjects.values_list('id', flat=True)
        student_count = User.objects.filter(
            role='student',
            enrollments__subject_id__in=subject_ids,
            enrollments__status=Enrollment.Status.ACTIVE,
        ).distinct().count()
        return Response({
            'subject_count': subjects.count(),
            'course_count': courses.count(),
            'lesson_count': Lesson.objects.filter(course__in=courses).count(),
            'student_count': student_count,
            'material_count': Material.objects.filter(course__in=courses).count(),
            'pending_submissions': Submission.objects.filter(
                assignment__course__in=courses,
                graded_at__isnull=True,
            ).count(),
            'recent_courses': CourseSerializer(courses.order_by('-created_at')[:5], many=True, context={'request': request}).data,
            'recent_lessons': LessonSerializer(
                Lesson.objects.filter(course__in=courses).select_related('course').order_by('-id')[:5],
                many=True,
            ).data,
        })


class TeacherStudentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, TeacherOnly]

    def list(self, request, *args, **kwargs):
        queryset = User.objects.filter(
            role='student',
            enrollments__subject__teacher=request.user,
            enrollments__status=Enrollment.Status.ACTIVE,
        ).distinct()
        subject_id = request.query_params.get('subject')
        faculty_id = request.query_params.get('faculty')
        level_id = request.query_params.get('level')
        search = request.query_params.get('search', '').strip()
        if subject_id:
            queryset = queryset.filter(enrollments__subject_id=subject_id, enrollments__subject__teacher=request.user, enrollments__status=Enrollment.Status.ACTIVE)
        if faculty_id:
            queryset = queryset.filter(enrollments__subject__faculty_id=faculty_id, enrollments__subject__teacher=request.user, enrollments__status=Enrollment.Status.ACTIVE)
        if level_id:
            queryset = queryset.filter(enrollments__subject__level_id=level_id, enrollments__subject__teacher=request.user, enrollments__status=Enrollment.Status.ACTIVE)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(matricule__icontains=search)
            )
        queryset = queryset.distinct().order_by('last_name', 'first_name')
        rows = []
        for student in queryset:
            enrollments = Enrollment.objects.filter(
                student=student,
                subject__teacher=request.user,
                status=Enrollment.Status.ACTIVE,
            ).select_related('subject', 'subject__faculty', 'subject__level')
            rows.append({
                'id': student.id,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'email': student.email,
                'matricule': student.matricule,
                'avatar_url': f'/api/users/{student.pk}/avatar/' if student.avatar else '',
                'subjects': [{
                    'id': enrollment.subject_id,
                    'name': enrollment.subject.name,
                    'code': enrollment.subject.code,
                    'faculty': enrollment.subject.faculty.name,
                    'level': enrollment.subject.level.name,
                } for enrollment in enrollments],
            })
        return Response(rows)


class TeacherSubjectListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, TeacherOnly]
    serializer_class = SubjectSerializer

    def get_queryset(self):
        return Subject.objects.filter(teacher=self.request.user).select_related(
            'faculty', 'level', 'academic_year',
        ).annotate(
            course_count=Count('courses', distinct=True),
            student_count=Count(
                'enrollments__student',
                filter=Q(enrollments__status=Enrollment.Status.ACTIVE),
                distinct=True,
            ),
        ).distinct().order_by('name')

    def list(self, request, *args, **kwargs):
        subjects = self.get_queryset()
        data = self.get_serializer(subjects, many=True).data
        for row, subject in zip(data, subjects):
            row['course_count'] = subject.course_count
            row['student_count'] = subject.student_count
            row['faculty_name'] = subject.faculty.name
            row['level_name'] = subject.level.name
            row['academic_year_name'] = subject.academic_year.name
        return Response(data)


class StudentDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def get(self, request):
        courses = visible_courses(request.user)
        course_ids = courses.values_list('id', flat=True)
        lesson_ids = Lesson.objects.filter(
            course_id__in=course_ids,
            status=Lesson.Status.PUBLISHED,
        ).values_list('id', flat=True)
        assignments = Assignment.objects.filter(
            course_id__in=course_ids,
            is_published=True,
        )
        progress = LessonProgress.objects.filter(student=request.user, lesson_id__in=lesson_ids)
        pending_assignments = assignments.exclude(submissions__student=request.user)
        return Response({
            'subject_count': Enrollment.objects.filter(
                student=request.user,
                status=Enrollment.Status.ACTIVE,
            ).values('subject_id').distinct().count(),
            'course_count': courses.count(),
            'lesson_count': lesson_ids.count(),
            'completed_lesson_count': progress.filter(completed_at__isnull=False).count(),
            'material_count': accessible_materials(request.user).filter(course_id__in=course_ids).count(),
            'assignment_count': assignments.count(),
            'pending_assignment_count': pending_assignments.count(),
            'recent_courses': CourseSerializer(
                courses.order_by('-created_at')[:5],
                many=True,
                context={'request': request},
            ).data,
            'recent_lessons': LessonSerializer(
                Lesson.objects.filter(id__in=lesson_ids).select_related('course').order_by('-published_at', '-id')[:5],
                many=True,
            ).data,
        })


class StudentSubjectListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def list(self, request, *args, **kwargs):
        subjects = Subject.objects.filter(
            enrollments__student=request.user,
            enrollments__status=Enrollment.Status.ACTIVE,
        ).select_related('faculty', 'level', 'academic_year').annotate(
            course_count=Count(
                'courses',
                filter=Q(courses__status=Course.Status.PUBLISHED),
                distinct=True,
            ),
        ).distinct().order_by('name')
        search = request.query_params.get('search', '').strip()
        if search:
            subjects = subjects.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(faculty__name__icontains=search)
                | Q(level__name__icontains=search)
            )
        return Response([{
            'id': subject.id,
            'code': subject.code,
            'name': subject.name,
            'description': subject.description,
            'faculty': subject.faculty.name,
            'level': subject.level.name,
            'academic_year': subject.academic_year.name,
            'course_count': subject.course_count,
        } for subject in subjects])


class StudentProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def get(self, request):
        from accounts.serializers import UserSerializer

        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        from accounts.serializers import UserSerializer

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StudentChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        if not current_password or not new_password:
            raise serializers.ValidationError({
                'detail': 'Le mot de passe actuel et le nouveau mot de passe sont obligatoires.',
            })
        if not request.user.check_password(current_password):
            raise serializers.ValidationError({'current_password': 'Le mot de passe actuel est incorrect.'})
        validate_password(new_password, request.user)
        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Mot de passe modifié avec succès.'})


class StudentLessonProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def get_lesson(self, request, lesson_pk):
        return get_object_or_404(
            Lesson.objects.select_related('course'),
            pk=lesson_pk,
            status=Lesson.Status.PUBLISHED,
            course__status=Course.Status.PUBLISHED,
            course__subject__enrollments__student=request.user,
            course__subject__enrollments__status=Enrollment.Status.ACTIVE,
        )

    def get(self, request, lesson_pk):
        lesson = self.get_lesson(request, lesson_pk)
        progress, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
        progress.save(update_fields=['last_accessed_at'])
        return Response({
            'lesson': lesson.pk,
            'completed': progress.completed_at is not None,
            'completed_at': progress.completed_at,
        })

    def post(self, request, lesson_pk):
        lesson = self.get_lesson(request, lesson_pk)
        completed = request.data.get('completed')
        if not isinstance(completed, bool):
            raise serializers.ValidationError({'completed': 'Cette valeur doit être vraie ou fausse.'})
        progress, _ = LessonProgress.objects.get_or_create(student=request.user, lesson=lesson)
        progress.completed_at = timezone.now() if completed else None
        progress.save(update_fields=['completed_at', 'last_accessed_at'])
        return Response({
            'lesson': lesson.pk,
            'completed': progress.completed_at is not None,
            'completed_at': progress.completed_at,
        })


class StudentProgressListView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def get(self, request):
        progress = LessonProgress.objects.filter(
            student=request.user,
            lesson__status=Lesson.Status.PUBLISHED,
            lesson__course__status=Course.Status.PUBLISHED,
            lesson__course__subject__enrollments__student=request.user,
            lesson__course__subject__enrollments__status=Enrollment.Status.ACTIVE,
        ).values('lesson_id', 'completed_at').distinct()
        return Response([{
            'lesson': item['lesson_id'],
            'completed': item['completed_at'] is not None,
            'completed_at': item['completed_at'],
        } for item in progress])


class StudentGradedSubmissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated, StudentOnly]

    def get(self, request):
        submissions = Submission.objects.filter(
            student=request.user,
            graded_at__isnull=False,
        ).select_related('assignment__course', 'student')
        return Response(SubmissionSerializer(
            submissions,
            many=True,
            context={'request': request},
        ).data)


class AssignmentListCreateView(generics.ListCreateAPIView):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Assignment.objects.select_related('course', 'course__teacher', 'course__subject', 'course__subject__faculty')
        if user.is_teacher:
            queryset = queryset.filter(course__in=teacher_courses(user))
        elif user.is_student:
            queryset = queryset.filter(
                course__subject__enrollments__student=user,
                course__subject__enrollments__status=Enrollment.Status.ACTIVE,
                course__status=Course.Status.PUBLISHED,
                is_published=True,
            )
        course_id = self.request.query_params.get('course')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(instructions__icontains=search))
        if self.request.user.is_teacher:
            published = self.request.query_params.get('published')
            if published in {'true', 'false'}:
                queryset = queryset.filter(is_published=published == 'true')
        return queryset.distinct()

    def create(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas créer un devoir.')
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = get_object_or_404(visible_courses(request.user), pk=request.data.get('course'))
        if request.user.is_teacher and not is_course_assigned_to_teacher(request.user, course):
            self.permission_denied(request, message='Ce cours ne vous appartient pas.')
        serializer.save(course=course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AssignmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AssignmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Assignment.objects.select_related('course', 'course__teacher', 'course__subject__faculty')
        if user.is_admin:
            return queryset
        if user.is_teacher:
            return queryset.filter(course__in=teacher_courses(user))
        return queryset.filter(
            course__subject__enrollments__student=user,
            course__subject__enrollments__status=Enrollment.Status.ACTIVE,
            course__status=Course.Status.PUBLISHED,
            is_published=True,
        ).distinct()

    def update(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas modifier ce devoir.')
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if not (request.user.is_admin or request.user.is_teacher):
            self.permission_denied(request, message='Vous ne pouvez pas supprimer ce devoir.')
        return super().destroy(request, *args, **kwargs)


class AssignmentSubmissionListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_assignment(self, request, assignment_pk):
        assignments = Assignment.objects.select_related('course', 'course__subject')
        if request.user.is_admin:
            return get_object_or_404(assignments, pk=assignment_pk)
        if request.user.is_teacher:
            return get_object_or_404(assignments.filter(course__in=teacher_courses(request.user)), pk=assignment_pk)
        return get_object_or_404(
            assignments.filter(
                course__subject__enrollments__student=request.user,
                course__subject__enrollments__status=Enrollment.Status.ACTIVE,
                course__status=Course.Status.PUBLISHED,
                is_published=True,
            ).distinct(),
            pk=assignment_pk,
        )

    def get(self, request, assignment_pk):
        assignment = self.get_assignment(request, assignment_pk)
        queryset = Submission.objects.filter(assignment=assignment).select_related('student')
        if request.user.is_student:
            queryset = queryset.filter(student=request.user)
        return Response(SubmissionSerializer(queryset, many=True, context={'request': request}).data)

    def post(self, request, assignment_pk):
        if not request.user.is_student:
            return Response({'detail': 'Seuls les étudiants peuvent remettre un devoir.'}, status=status.HTTP_403_FORBIDDEN)
        assignment = self.get_assignment(request, assignment_pk)
        if assignment.due_at and assignment.due_at < timezone.now():
            return Response({'detail': 'La date limite de remise est dépassée.'}, status=status.HTTP_400_BAD_REQUEST)
        submission = Submission.objects.filter(assignment=assignment, student=request.user).first()
        if submission and submission.is_graded:
            return Response({'detail': 'Ce devoir a déjà été corrigé et ne peut plus être modifié.'}, status=status.HTTP_400_BAD_REQUEST)
        serializer = SubmissionSerializer(
            submission,
            data=request.data,
            partial=submission is not None,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment, student=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK if submission else status.HTTP_201_CREATED)


class SubmissionDetailView(generics.RetrieveUpdateAPIView):
    serializer_class = SubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Submission.objects.select_related('assignment__course', 'student')
        if user.is_admin:
            return queryset
        if user.is_teacher:
            return queryset.filter(assignment__course__in=teacher_courses(user))
        return queryset.filter(student=user)

    def update(self, request, *args, **kwargs):
        if not (request.user.is_teacher or request.user.is_admin):
            self.permission_denied(request, message='Vous ne pouvez pas corriger ce devoir.')
        return super().update(request, *args, **kwargs)


class SubmissionDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        queryset = Submission.objects.select_related('assignment__course', 'student')
        if request.user.is_teacher:
            queryset = queryset.filter(assignment__course__in=teacher_courses(request.user))
        elif request.user.is_student:
            queryset = queryset.filter(student=request.user)
        submission = get_object_or_404(queryset, pk=pk)
        return FileResponse(submission.file.open('rb'), as_attachment=True, filename=os.path.basename(submission.file.name))


class SubmissionCorrectedDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        queryset = Submission.objects.select_related('assignment__course', 'student')
        if request.user.is_teacher:
            queryset = queryset.filter(assignment__course__in=teacher_courses(request.user))
        elif request.user.is_student:
            queryset = queryset.filter(student=request.user)
        submission = get_object_or_404(queryset, pk=pk)
        if not submission.corrected_file:
            return Response({'detail': 'Aucun fichier corrigé n’est disponible.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            submission.corrected_file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(submission.corrected_file.name),
        )


class AssignmentReferenceDownloadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        assignments = Assignment.objects.select_related('course')
        if request.user.is_teacher:
            assignments = assignments.filter(course__in=teacher_courses(request.user))
        elif request.user.is_student:
            assignments = assignments.filter(
                course__subject__enrollments__student=request.user,
                course__subject__enrollments__status=Enrollment.Status.ACTIVE,
                course__status=Course.Status.PUBLISHED,
                is_published=True,
            ).distinct()
        assignment = get_object_or_404(assignments, pk=pk)
        if not assignment.reference_file:
            return Response({'detail': 'Aucun document de référence.'}, status=status.HTTP_404_NOT_FOUND)
        return FileResponse(
            assignment.reference_file.open('rb'),
            as_attachment=True,
            filename=os.path.basename(assignment.reference_file.name),
        )


class TeacherProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated, TeacherOnly]

    def get(self, request):
        from accounts.serializers import UserSerializer

        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        from accounts.serializers import UserSerializer

        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class TeacherChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated, TeacherOnly]

    def post(self, request):
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        if not current_password or not new_password:
            raise serializers.ValidationError({
                'detail': 'Le mot de passe actuel et le nouveau mot de passe sont obligatoires.',
            })
        if not request.user.check_password(current_password):
            raise serializers.ValidationError({'current_password': 'Le mot de passe actuel est incorrect.'})
        validate_password(new_password, request.user)
        request.user.set_password(new_password)
        request.user.save(update_fields=['password'])
        update_session_auth_hash(request, request.user)
        return Response({'detail': 'Mot de passe modifié avec succès.'})
