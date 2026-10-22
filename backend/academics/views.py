from rest_framework import generics, permissions, serializers
from rest_framework.permissions import SAFE_METHODS

from accounts.audit import log_admin_action
from accounts.permissions import IsAdminUser
from courses.models import Course
from courses.social import create_admin_activity_post
from .models import AcademicLevel, AcademicYear, Faculty, Subject
from .serializers import AcademicLevelSerializer, AcademicYearSerializer, FacultySerializer, SubjectSerializer


class AdminWriteMixin:
    def get_permissions(self):
        if self.request.method not in SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        log_admin_action(self.request.user, 'create', instance.__class__.__name__, instance.pk, f'Création : {instance}')

    def perform_update(self, serializer):
        instance = serializer.save()
        log_admin_action(self.request.user, 'update', instance.__class__.__name__, instance.pk, f'Mise à jour : {instance}')


class FacultyListCreateView(AdminWriteMixin, generics.ListCreateAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [permissions.AllowAny()]
        return super().get_permissions()


class FacultyDetailView(AdminWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    def perform_destroy(self, instance):
        if instance.subjects.exists() or instance.levels.exists():
            raise serializers.ValidationError('Cette filière est encore utilisée par des niveaux ou des matières. Réaffectez-les avant suppression.')
        log_admin_action(self.request.user, 'delete', 'Faculty', instance.pk, f'Suppression de la filière {instance.name}')
        instance.delete()


class AcademicLevelListCreateView(AdminWriteMixin, generics.ListCreateAPIView):
    queryset = AcademicLevel.objects.all()
    serializer_class = AcademicLevelSerializer


class AcademicLevelDetailView(AdminWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicLevel.objects.all()
    serializer_class = AcademicLevelSerializer
    def perform_destroy(self, instance):
        if instance.subjects.exists():
            raise serializers.ValidationError('Ce niveau est encore utilisé par des matières. Réaffectez-les avant suppression.')
        log_admin_action(self.request.user, 'delete', 'AcademicLevel', instance.pk, f'Suppression du niveau {instance.name}')
        instance.delete()


class AcademicYearListCreateView(AdminWriteMixin, generics.ListCreateAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer


class AcademicYearDetailView(AdminWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    def perform_destroy(self, instance):
        if instance.subjects.exists() or instance.enrollments.exists():
            raise serializers.ValidationError('Cette année académique est encore liée à des matières ou des inscriptions et ne peut pas être supprimée.')
        log_admin_action(self.request.user, 'delete', 'AcademicYear', instance.pk, f'Suppression de l’année {instance.name}')
        instance.delete()


class SubjectListCreateView(AdminWriteMixin, generics.ListCreateAPIView):
    queryset = Subject.objects.select_related('faculty', 'level', 'academic_year', 'teacher').all()
    serializer_class = SubjectSerializer

    def perform_create(self, serializer):
        subject = serializer.save()
        log_admin_action(
            self.request.user, 'create', 'Subject', subject.pk, f'Création : {subject}',
        )
        create_admin_activity_post(
            self.request.user,
            'subject',
            f'Nouvelle matière : {subject.name}',
            f'L’administration a ajouté la matière « {subject.name} » ({subject.code}) dans la filière « {subject.faculty.name} ».',
            subject=subject,
        )

    def get_queryset(self):
        queryset = super().get_queryset()
        faculty_id = self.request.query_params.get('faculty')
        academic_year_id = self.request.query_params.get('academic_year')
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(academic_year__is_active=True)
            if faculty_id:
                queryset = queryset.filter(faculty_id=faculty_id)
            return queryset
        if self.request.user.is_admin:
            pass
        elif self.request.user.is_teacher:
            queryset = queryset.filter(teacher=self.request.user)
        else:
            queryset = queryset.filter(enrollments__student=self.request.user, enrollments__status='active').distinct()
        if faculty_id:
            queryset = queryset.filter(faculty_id=faculty_id)
        if academic_year_id:
            queryset = queryset.filter(academic_year_id=academic_year_id)
        return queryset

    def get_permissions(self):
        if self.request.method in SAFE_METHODS and not self.request.user.is_authenticated:
            return [permissions.AllowAny()]
        if self.request.method not in SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()


class SubjectDetailView(AdminWriteMixin, generics.RetrieveUpdateDestroyAPIView):
    queryset = Subject.objects.select_related('faculty', 'level', 'academic_year', 'teacher').all()
    serializer_class = SubjectSerializer

    def perform_update(self, serializer):
        subject = self.get_object()
        previous = {
            'code': subject.code,
            'name': subject.name,
            'description': subject.description,
            'faculty_id': subject.faculty_id,
            'level_id': subject.level_id,
            'academic_year_id': subject.academic_year_id,
            'teacher_id': subject.teacher_id,
        }
        subject = serializer.save()
        log_admin_action(
            self.request.user, 'update', 'Subject', subject.pk, f'Mise à jour : {subject}',
        )
        changed_fields = [
            field for field, value in previous.items()
            if getattr(subject, field) != value
        ]
        if changed_fields:
            labels = {
                'code': 'code',
                'name': 'nom',
                'description': 'description',
                'faculty_id': 'filière',
                'level_id': 'niveau',
                'academic_year_id': 'année académique',
                'teacher_id': 'professeur affecté',
            }
            create_admin_activity_post(
                self.request.user,
                'subject',
                f'Mise à jour de la matière : {subject.name}',
                f'L’administration a modifié la matière « {subject.name} » ({", ".join(labels[field] for field in changed_fields)}).',
                subject=subject,
            )

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_admin:
            return queryset
        if self.request.user.is_teacher:
            return queryset.filter(teacher=self.request.user)
        return queryset.filter(enrollments__student=self.request.user, enrollments__status='active').distinct()

    def get_permissions(self):
        if self.request.method not in SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        if instance.enrollments.exists() or Course.objects.filter(subject=instance).exists():
            raise serializers.ValidationError('Cette matière possède des inscriptions ou des cours. Retirez-les ou réaffectez-les avant suppression.')
        log_admin_action(self.request.user, 'delete', 'Subject', instance.pk, f'Suppression de la matière {instance.code}')
        create_admin_activity_post(
            self.request.user,
            'subject',
            f'Suppression de la matière : {instance.name}',
            f'L’administration a supprimé la matière « {instance.name} » ({instance.code}).',
        )
        instance.delete()
