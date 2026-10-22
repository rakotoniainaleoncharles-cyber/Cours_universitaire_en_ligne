import mimetypes
import os

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db import models
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .permissions import IsAdminUser
from .audit import log_admin_action
from .models import AdminAuditLog
from .serializers import AdminUserSerializer, LoginSerializer, PasswordResetSerializer, RegisterSerializer, UserSerializer

UserModel = get_user_model()


class AdminDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get(self, request):
        from academics.models import AcademicLevel, AcademicYear, Faculty, Subject
        from courses.models import Assignment, Course, Lesson, Material, Submission
        from users.models import Enrollment
        from django.urls import reverse

        users = UserModel.objects.all()
        return Response({
            'student_count': users.filter(role='student').count(),
            'pending_approval_count': users.filter(is_approved=False).count(),
            'teacher_count': users.filter(role='teacher').count(),
            'active_user_count': users.filter(is_active=True).count(),
            'inactive_user_count': users.filter(is_active=False).count(),
            'faculty_count': Faculty.objects.count(),
            'level_count': AcademicLevel.objects.count(),
            'academic_year_count': AcademicYear.objects.count(),
            'subject_count': Subject.objects.count(),
            'course_count': Course.objects.count(),
            'lesson_count': Lesson.objects.count(),
            'material_count': Material.objects.count(),
            'enrollment_count': Enrollment.objects.count(),
            'assignment_count': Assignment.objects.count(),
            'submission_count': Submission.objects.count(),
            'recent_users': [{
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'is_active': user.is_active,
                'is_approved': user.is_approved,
                'created_at': user.created_at,
                'avatar_url': reverse('user-avatar', kwargs={'pk': user.pk}) if user.avatar else '',
            } for user in users.order_by('-created_at')[:8]],
            'recent_activity': list(AdminAuditLog.objects.select_related('actor').values(
                'id', 'action', 'resource_type', 'resource_id', 'description', 'created_at',
                'actor__email',
            )[:8]),
        })


class AdminAuditLogListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def list(self, request, *args, **kwargs):
        queryset = AdminAuditLog.objects.select_related('actor').all()
        search = request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                models.Q(description__icontains=search)
                | models.Q(resource_type__icontains=search)
                | models.Q(action__icontains=search)
                | models.Q(actor__email__icontains=search)
            )
        return Response([{
            'id': row.id,
            'action': row.action,
            'resource_type': row.resource_type,
            'resource_id': row.resource_id,
            'description': row.description,
            'created_at': row.created_at,
            'actor_email': row.actor.email if row.actor else None,
        } for row in queryset[:200]])


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        refresh = RefreshToken.for_user(user)
        return Response(
            {'refresh': str(refresh), 'access': str(refresh.access_token), 'user': UserSerializer(user).data},
            status=status.HTTP_200_OK,
        )


class StudentRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.save()
        detail = (
            'Votre inscription étudiante a été envoyée à l’administration. Vous pourrez vous connecter après validation.'
            if user.role == 'student'
            else 'Votre demande de compte professeur a été envoyée. Vous pourrez vous connecter après validation par l’administration.'
        )
        return Response({
            'pending_approval': True,
            'detail': detail,
        }, status=status.HTTP_201_CREATED)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        if 'avatar' not in request.data:
            raise serializers.ValidationError({'avatar': 'La photo de profil est obligatoire.'})
        serializer = UserSerializer(request.user, data={'avatar': request.data['avatar']}, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class UserAvatarView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = get_object_or_404(UserModel, pk=pk)
        if not user.avatar:
            return HttpResponse(status=status.HTTP_404_NOT_FOUND)
        extension = os.path.splitext(user.avatar.name)[1].lower()
        content_type = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp',
        }.get(extension, 'application/octet-stream')
        response = FileResponse(user.avatar.open('rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(user.avatar.name)}"'
        response['X-Content-Type-Options'] = 'nosniff'
        response['Cache-Control'] = 'private, no-store'
        return response


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            raise serializers.ValidationError({'refresh': 'Le jeton de renouvellement est obligatoire.'})
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError as error:
            raise serializers.ValidationError({'refresh': 'Le jeton de renouvellement est invalide ou expiré.'}) from error
        return Response({'detail': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)


class UserListCreateView(generics.ListCreateAPIView):
    queryset = UserModel.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = UserModel.objects.all()
        role = self.request.query_params.get('role')
        search = self.request.query_params.get('search')
        active = self.request.query_params.get('is_active')
        ordering = self.request.query_params.get('ordering', '-created_at')
        faculty = self.request.query_params.get('faculty')
        level = self.request.query_params.get('level')
        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
                | models.Q(matricule__icontains=search)
                | models.Q(phone__icontains=search)
            )
        if active in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')
        if faculty:
            queryset = queryset.filter(
                models.Q(subjects__faculty_id=faculty)
                | models.Q(enrollments__subject__faculty_id=faculty)
            )
        if level:
            queryset = queryset.filter(
                models.Q(subjects__level_id=level)
                | models.Q(enrollments__subject__level_id=level)
            )
        if ordering in {'first_name', '-first_name', 'last_name', '-last_name', 'created_at', '-created_at', 'email', '-email'}:
            queryset = queryset.order_by(ordering)
        return queryset.distinct()

    def perform_create(self, serializer):
        user = serializer.save()
        log_admin_action(self.request.user, 'create', 'user', user.pk, f'Création du compte {user.email}')


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserModel.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_admin and str(request.data.get('is_active')).lower() in {'false', '0'}:
            raise serializers.ValidationError({'is_active': 'Le compte administrateur unique ne peut pas être désactivé.'})
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_admin:
            raise serializers.ValidationError('Le compte administrateur unique ne peut pas être supprimé.')
        has_related_records = (
            instance.courses.exists()
            or instance.materials.exists()
            or instance.enrollments.exists()
            or instance.submissions.exists()
        )
        if has_related_records:
            raise serializers.ValidationError('Ce compte possède des données pédagogiques ou des inscriptions. Désactivez-le ou réaffectez les données avant suppression.')
        log_admin_action(request.user, 'delete', 'user', instance.pk, f'Suppression du compte {instance.email}')
        return super().destroy(request, *args, **kwargs)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_admin_action(self.request.user, 'update', 'user', instance.pk, f'Mise à jour du compte {instance.email}')


class ResetPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        user = get_object_or_404(UserModel.objects.all(), pk=pk)
        if user.is_admin:
            raise serializers.ValidationError('Le mot de passe administrateur ne peut pas être réinitialisé depuis cette fonction.')
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        log_admin_action(request.user, 'reset_password', 'user', user.pk, f'Réinitialisation du mot de passe de {user.email}')
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'}, status=status.HTTP_200_OK)


class TeacherProfileListView(generics.ListAPIView):
    queryset = UserModel.objects.filter(role='teacher')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
