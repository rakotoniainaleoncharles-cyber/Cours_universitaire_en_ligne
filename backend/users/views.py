from rest_framework import generics, permissions
from rest_framework.permissions import SAFE_METHODS
from django.db import models

from accounts.audit import log_admin_action
from accounts.permissions import IsAdminUser
from .models import Enrollment
from .serializers import EnrollmentSerializer


class EnrollmentListCreateView(generics.ListCreateAPIView):
    queryset = Enrollment.objects.select_related('student', 'subject', 'subject__faculty', 'subject__level', 'subject__academic_year', 'subject__teacher')
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_admin:
            subject = self.request.query_params.get('subject')
            student = self.request.query_params.get('student')
            faculty = self.request.query_params.get('faculty')
            level = self.request.query_params.get('level')
            year = self.request.query_params.get('academic_year')
            enrollment_status = self.request.query_params.get('status')
            search = self.request.query_params.get('search', '').strip()
            if subject:
                queryset = queryset.filter(subject_id=subject)
            if student:
                queryset = queryset.filter(student_id=student)
            if faculty:
                queryset = queryset.filter(subject__faculty_id=faculty)
            if level:
                queryset = queryset.filter(subject__level_id=level)
            if year:
                queryset = queryset.filter(academic_year_id=year)
            if enrollment_status in Enrollment.Status.values:
                queryset = queryset.filter(status=enrollment_status)
            if search:
                queryset = queryset.filter(
                    models.Q(student__first_name__icontains=search)
                    | models.Q(student__last_name__icontains=search)
                    | models.Q(student__email__icontains=search)
                    | models.Q(subject__name__icontains=search)
                    | models.Q(subject__code__icontains=search)
                )
            return queryset
        if self.request.user.is_teacher:
            return queryset.filter(subject__teacher=self.request.user, status=Enrollment.Status.ACTIVE)
        return queryset.filter(student=self.request.user, status=Enrollment.Status.ACTIVE)

    def perform_create(self, serializer):
        enrollment = serializer.save()
        log_admin_action(
            self.request.user, 'create', 'Enrollment', enrollment.pk,
            f'Inscription de {enrollment.student.email} à {enrollment.subject.code}',
        )

    def get_permissions(self):
        if self.request.method not in SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()


class EnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Enrollment.objects.select_related('student', 'subject', 'subject__faculty', 'subject__level', 'subject__academic_year', 'subject__teacher')
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.is_admin:
            return queryset
        if self.request.user.is_teacher:
            return queryset.filter(subject__teacher=self.request.user, status=Enrollment.Status.ACTIVE)
        return queryset.filter(student=self.request.user, status=Enrollment.Status.ACTIVE)

    def get_permissions(self):
        if self.request.method not in SAFE_METHODS:
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return super().get_permissions()

    def perform_update(self, serializer):
        enrollment = serializer.save()
        log_admin_action(
            self.request.user, 'update', 'Enrollment', enrollment.pk,
            f'Mise à jour de l’inscription de {enrollment.student.email} à {enrollment.subject.code}',
        )

    def perform_destroy(self, instance):
        log_admin_action(
            self.request.user, 'delete', 'Enrollment', instance.pk,
            f'Suppression de l’inscription de {instance.student.email} à {instance.subject.code}',
        )
        instance.delete()
