from pathlib import Path

root = Path(r"C:\Users\SÿaM\OneDrive\Documentos\DJANGO")
backend = root / "backend"
frontend = root / "frontend"

backend.mkdir(exist_ok=True)
frontend.mkdir(exist_ok=True)

# --- backend files ---
files = {
    "backend/requirements.txt": """Django==6.1.2
 djangorestframework==3.18.3
djangorestframework-simplejwt==5.5.1
django-cors-headers==4.9.0
PyMySQL==1.2.3
python-dotenv==1.2.4
Pillow==12.3.0
""",
    "backend/.env.example": """DJANGO_SECRET_KEY=change-me-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=university_db
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
FRONTEND_URL=http://localhost:5173
""",
    "backend/.env": """DJANGO_SECRET_KEY=dev-secret-key-change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
DB_NAME=university_db
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
FRONTEND_URL=http://localhost:5173
""",
    "backend/manage.py": """#!/usr/bin/env python
import os
import sys


def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
""",
    "backend/config/__init__.py": "",
    "backend/config/asgi.py": """import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_asgi_application()
""",
    "backend/config/wsgi.py": """import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
""",
    "backend/config/settings.py": """from datetime import timedelta
import os
from pathlib import Path

import pymysql
from dotenv import load_dotenv

pymysql.install_as_MySQLdb()

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'django-insecure-change-me')
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    'rest_framework_simplejwt',
    'accounts',
    'academics',
    'courses',
    'users',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'university_db'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5173',
    'http://127.0.0.1:5173',
]
""",
    "backend/config/urls.py": """from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('accounts.urls')),
    path('api/', include('academics.urls')),
    path('api/', include('courses.urls')),
    path('api/', include('users.urls')),
]
""",
    "backend/accounts/__init__.py": "",
    "backend/accounts/apps.py": """from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'
""",
    "backend/accounts/managers.py": """from django.contrib.auth.base_user import BaseUserManager


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Le superutilisateur doit avoir is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Le superutilisateur doit avoir is_superuser=True')
        return self.create_user(email, password, **extra_fields)
""",
    "backend/accounts/models.py": """from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=[('admin', 'Administrateur'), ('teacher', 'Professeur'), ('student', 'Étudiant')],
        default='student',
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    objects = UserManager()

    class Meta:
        ordering = ['last_name', 'first_name']

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def is_teacher(self):
        return self.role == 'teacher'

    @property
    def is_student(self):
        return self.role == 'student'

    def __str__(self):
        return self.email
""",
    "backend/accounts/admin.py": """from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_staff')
    fieldsets = UserAdmin.fieldsets + ((None, {'fields': ('role', 'avatar')}),)
    add_fieldsets = UserAdmin.add_fieldsets + ((None, {'fields': ('email', 'first_name', 'last_name', 'role', 'avatar')}),)
""",
    "backend/accounts/permissions.py": """from rest_framework.permissions import BasePermission


class IsAdminUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsTeacherUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_teacher)


class IsStudentUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_student)


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return bool(request.user and request.user.is_authenticated and (request.user.is_admin or obj == request.user))
""",
    "backend/accounts/serializers.py": """from django.contrib.auth import authenticate
from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 'avatar', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role']

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Identifiants invalides.')
        if not user.is_active:
            raise serializers.ValidationError('Ce compte est désactivé.')
        return {'user': user}


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError('Le mot de passe doit contenir au moins 8 caractères.')
        return value
""",
    "backend/accounts/views.py": """from django.contrib.auth import get_user_model
from django.db import models
from rest_framework import generics, permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import User
from .permissions import IsAdminUser, IsOwnerOrAdmin
from .serializers import LoginSerializer, PasswordResetSerializer, UserSerializer

UserModel = get_user_model()


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


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data['refresh']
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass
        return Response({'detail': 'Déconnexion réussie.'}, status=status.HTTP_200_OK)


class UserListCreateView(generics.ListCreateAPIView):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        queryset = UserModel.objects.all()
        role = self.request.query_params.get('role')
        search = self.request.query_params.get('search')
        if role:
            queryset = queryset.filter(role=role)
        if search:
            queryset = queryset.filter(
                models.Q(first_name__icontains=search)
                | models.Q(last_name__icontains=search)
                | models.Q(email__icontains=search)
            )
        return queryset

    def perform_create(self, serializer):
        if 'password' not in self.request.data:
            raise serializers.ValidationError({'password': 'Le mot de passe est obligatoire.'})
        password = self.request.data['password']
        serializer.save(password=password)


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserModel.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance == request.user:
            raise serializers.ValidationError('Impossible de supprimer votre propre compte.')
        return super().destroy(request, *args, **kwargs)


class ResetPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        user = UserModel.objects.get(pk=pk)
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])
        return Response({'detail': 'Mot de passe réinitialisé avec succès.'}, status=status.HTTP_200_OK)


class TeacherProfileListView(generics.ListAPIView):
    queryset = UserModel.objects.filter(role='teacher')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
""",
    "backend/accounts/urls.py": """from django.urls import path

from .views import LoginView, LogoutView, MeView, ResetPasswordView, TeacherProfileListView, UserDetailView, UserListCreateView

urlpatterns = [
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('users/', UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('users/<int:pk>/reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('teachers/', TeacherProfileListView.as_view(), name='teacher-list'),
]
""",
    "backend/academics/__init__.py": "",
    "backend/academics/apps.py": """from django.apps import AppConfig


class AcademicsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academics'
""",
    "backend/academics/models.py": """from django.conf import settings
from django.db import models


class Faculty(models.Model):
    name = models.CharField(max_length=150, unique=True)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class AcademicLevel(models.Model):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name


class Subject(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    faculty = models.ForeignKey('Faculty', related_name='subjects', on_delete=models.CASCADE)
    level = models.ForeignKey('AcademicLevel', related_name='subjects', on_delete=models.CASCADE)
    academic_year = models.ForeignKey('AcademicYear', related_name='subjects', on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='subjects', null=True, blank=True, on_delete=models.SET_NULL)
    description = models.TextField(blank=True)

    def __str__(self):
        return f'{self.code} - {self.name}'
""",
    "backend/academics/serializers.py": """from rest_framework import serializers

from .models import AcademicLevel, AcademicYear, Faculty, Subject


class FacultySerializer(serializers.ModelSerializer):
    class Meta:
        model = Faculty
        fields = '__all__'


class AcademicLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicLevel
        fields = '__all__'


class AcademicYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicYear
        fields = '__all__'


class SubjectSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    level_name = serializers.CharField(source='level.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'code', 'name', 'description', 'faculty', 'faculty_name', 'level', 'level_name', 'academic_year', 'teacher', 'teacher_name']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.email
        return None
""",
    "backend/academics/views.py": """from rest_framework import generics, permissions

from .models import AcademicLevel, AcademicYear, Faculty, Subject
from .serializers import AcademicLevelSerializer, AcademicYearSerializer, FacultySerializer, SubjectSerializer


class FacultyListCreateView(generics.ListCreateAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [permissions.IsAuthenticated]


class FacultyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Faculty.objects.all()
    serializer_class = FacultySerializer
    permission_classes = [permissions.IsAuthenticated]


class AcademicLevelListCreateView(generics.ListCreateAPIView):
    queryset = AcademicLevel.objects.all()
    serializer_class = AcademicLevelSerializer
    permission_classes = [permissions.IsAuthenticated]


class AcademicLevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicLevel.objects.all()
    serializer_class = AcademicLevelSerializer
    permission_classes = [permissions.IsAuthenticated]


class AcademicYearListCreateView(generics.ListCreateAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [permissions.IsAuthenticated]


class AcademicYearDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = AcademicYear.objects.all()
    serializer_class = AcademicYearSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubjectListCreateView(generics.ListCreateAPIView):
    queryset = Subject.objects.select_related('faculty', 'level', 'academic_year', 'teacher').all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Subject.objects.select_related('faculty', 'level', 'academic_year', 'teacher').all()
    serializer_class = SubjectSerializer
    permission_classes = [permissions.IsAuthenticated]
""",
    "backend/academics/urls.py": """from django.urls import path

from .views import (
    AcademicLevelDetailView,
    AcademicLevelListCreateView,
    AcademicYearDetailView,
    AcademicYearListCreateView,
    FacultyDetailView,
    FacultyListCreateView,
    SubjectDetailView,
    SubjectListCreateView,
)

urlpatterns = [
    path('faculties/', FacultyListCreateView.as_view(), name='faculty-list'),
    path('faculties/<int:pk>/', FacultyDetailView.as_view(), name='faculty-detail'),
    path('levels/', AcademicLevelListCreateView.as_view(), name='academic-level-list'),
    path('levels/<int:pk>/', AcademicLevelDetailView.as_view(), name='academic-level-detail'),
    path('academic-years/', AcademicYearListCreateView.as_view(), name='academic-year-list'),
    path('academic-years/<int:pk>/', AcademicYearDetailView.as_view(), name='academic-year-detail'),
    path('subjects/', SubjectListCreateView.as_view(), name='subject-list'),
    path('subjects/<int:pk>/', SubjectDetailView.as_view(), name='subject-detail'),
]
""",
    "backend/courses/__init__.py": "",
    "backend/courses/apps.py": """from django.apps import AppConfig


class CoursesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'courses'
""",
    "backend/courses/models.py": """from django.conf import settings
from django.db import models

from academics.models import Subject


class Course(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    subject = models.ForeignKey(Subject, related_name='courses', on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='courses', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content = models.TextField()
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['published_at']

    def __str__(self):
        return self.title


class Material(models.Model):
    course = models.ForeignKey(Course, related_name='materials', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/%Y/%m/%d/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='materials', on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
""",
    "backend/courses/serializers.py": """from rest_framework import serializers

from .models import Course, Lesson, Material


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'content', 'published_at']


class MaterialSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Material
        fields = ['id', 'course', 'title', 'description', 'file', 'file_url', 'uploaded_by', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_by', 'uploaded_at', 'file_url']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request is not None:
            return request.build_absolute_uri(obj.file.url)
        return obj.file.url if obj.file else None

    def validate_file(self, value):
        allowed_extensions = ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.png', '.jpg', '.jpeg']
        if value.size > 20 * 1024 * 1024:
            raise serializers.ValidationError('Le fichier ne doit pas dépasser 20 Mo.')
        ext = str(value.name).lower()
        if not any(ext.endswith(item) for item in allowed_extensions):
            raise serializers.ValidationError('Type de fichier non autorisé.')
        return value


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    materials = MaterialSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'slug', 'description', 'subject', 'subject_name', 'teacher', 'teacher_name', 'created_at', 'updated_at', 'published_at', 'lessons', 'materials']
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at', 'lessons', 'materials']

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.email
        return None
""",
    "backend/courses/views.py": """from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Course, Lesson, Material
from .serializers import CourseSerializer, LessonSerializer, MaterialSerializer


class CourseListCreateView(generics.ListCreateAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = Course.objects.select_related('subject', 'teacher').prefetch_related('lessons', 'materials')
        if user.is_admin:
            return qs
        if user.is_teacher:
            return qs.filter(teacher=user)
        return qs.filter(subject__in=[enrollment.subject for enrollment in user.enrollments.all()]) if hasattr(user, 'enrollments') else qs.none()

    def perform_create(self, serializer):
        if not self.request.user.is_admin and not self.request.user.is_teacher:
            self.permission_denied(self.request, message='Vous ne pouvez pas créer de cours.')
        serializer.save(teacher=self.request.user)


class CourseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Course.objects.select_related('subject', 'teacher').prefetch_related('lessons', 'materials')
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Course.objects.all()
        if user.is_teacher:
            return Course.objects.filter(teacher=user)
        return Course.objects.filter(subject__in=[enrollment.subject for enrollment in user.enrollments.all()]) if hasattr(user, 'enrollments') else Course.objects.none()

    def delete(self, request, *args, **kwargs):
        course = self.get_object()
        if not (request.user.is_admin or request.user == course.teacher):
            return Response({'detail': 'Vous ne pouvez pas supprimer ce cours.'}, status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)


class LessonListCreateView(generics.ListCreateAPIView):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        if self.request.user.is_admin or self.request.user == course.teacher or self.request.user.is_student:
            return Lesson.objects.filter(course=course)
        return Lesson.objects.none()

    def perform_create(self, serializer):
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        if not (self.request.user.is_admin or self.request.user == course.teacher):
            self.permission_denied(self.request, message='Vous ne pouvez pas ajouter une leçon à ce cours.')
        serializer.save(course=course)


class LessonDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Lesson.objects.all()
        if user.is_teacher:
            return Lesson.objects.filter(course__teacher=user)
        return Lesson.objects.filter(course__subject__in=[enrollment.subject for enrollment in user.enrollments.all()]) if hasattr(user, 'enrollments') else Lesson.objects.none()


class MaterialListCreateView(generics.ListCreateAPIView):
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        if user.is_admin or user == course.teacher or user.is_student:
            return Material.objects.filter(course=course)
        return Material.objects.none()

    def perform_create(self, serializer):
        course = get_object_or_404(Course, pk=self.kwargs['course_pk'])
        if not (self.request.user.is_admin or self.request.user == course.teacher):
            self.permission_denied(self.request, message='Vous ne pouvez pas téléverser un document pour ce cours.')
        serializer.save(course=course, uploaded_by=self.request.user)


class MaterialDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Material.objects.all()
    serializer_class = MaterialSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin:
            return Material.objects.all()
        if user.is_teacher:
            return Material.objects.filter(course__teacher=user)
        return Material.objects.filter(course__subject__in=[enrollment.subject for enrollment in user.enrollments.all()]) if hasattr(user, 'enrollments') else Material.objects.none()


class CoursePublicListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = Course.objects.select_related('subject', 'teacher').prefetch_related('lessons', 'materials')
        serializer = CourseSerializer(qs, many=True, context={'request': request})
        return Response(serializer.data)
""",
    "backend/courses/urls.py": """from django.urls import path

from .views import (
    CourseDetailView,
    CourseListCreateView,
    CoursePublicListView,
    LessonDetailView,
    LessonListCreateView,
    MaterialDetailView,
    MaterialListCreateView,
)

urlpatterns = [
    path('courses/', CourseListCreateView.as_view(), name='course-list'),
    path('courses/public/', CoursePublicListView.as_view(), name='course-public-list'),
    path('courses/<int:pk>/', CourseDetailView.as_view(), name='course-detail'),
    path('courses/<int:course_pk>/lessons/', LessonListCreateView.as_view(), name='lesson-list'),
    path('lessons/<int:pk>/', LessonDetailView.as_view(), name='lesson-detail'),
    path('courses/<int:course_pk>/materials/', MaterialListCreateView.as_view(), name='material-list'),
    path('materials/<int:pk>/', MaterialDetailView.as_view(), name='material-detail'),
]
""",
    "backend/users/__init__.py": "",
    "backend/users/apps.py": """from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
""",
    "backend/users/models.py": """from django.conf import settings
from django.db import models

from academics.models import Subject


class Enrollment(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='enrollments', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name='enrollments', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'subject')

    def __str__(self):
        return f'{self.student.email} -> {self.subject.name}'
""",
    "backend/users/serializers.py": """from rest_framework import serializers

from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'
""",
    "backend/users/views.py": """from rest_framework import generics, permissions

from .models import Enrollment
from .serializers import EnrollmentSerializer


class EnrollmentListCreateView(generics.ListCreateAPIView):
    queryset = Enrollment.objects.select_related('student', 'subject')
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]


class EnrollmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Enrollment.objects.select_related('student', 'subject')
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
""",
    "backend/users/urls.py": """from django.urls import path

from .views import EnrollmentDetailView, EnrollmentListCreateView

urlpatterns = [
    path('enrollments/', EnrollmentListCreateView.as_view(), name='enrollment-list'),
    path('enrollments/<int:pk>/', EnrollmentDetailView.as_view(), name='enrollment-detail'),
]
""",
    "backend/users/admin.py": """from django.contrib import admin

from .models import Enrollment

admin.site.register(Enrollment)
""",
}

for rel_path, content in files.items():
    file_path = root / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')

# Frontend package.json and Vite setup
(frontend / 'package.json').write_text("""{
  "name": "university-portal",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.9",
    "lucide-react": "^0.468.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^7.1.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.4",
    "vite": "^6.0.11"
  }
}
""", encoding='utf-8')
(frontend / 'vite.config.js').write_text("""import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
  },
})
""", encoding='utf-8')
(frontend / 'index.html').write_text("""<!doctype html>
<html lang="fr">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Université</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
""", encoding='utf-8')
(frontend / 'src').mkdir(exist_ok=True)
(frontend / 'src' / 'main.jsx').write_text("""import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './styles/global.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
""", encoding='utf-8')
(frontend / 'src' / 'App.jsx').write_text("""import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import AdminDashboard from './pages/admin/AdminDashboard'
import StudentDashboard from './pages/student/StudentDashboard'
import TeacherDashboard from './pages/teacher/TeacherDashboard'
import { AuthProvider, useAuth } from './context/AuthContext'
import ProtectedRoute from './routes/ProtectedRoute'
import AppShell from './layouts/AppShell'

function AppContent() {
  const { user, isAuthenticated, loading } = useAuth()

  if (loading) {
    return <div className="loading-screen">Chargement...</div>
  }

  return (
    <Routes>
      <Route path="/" element={isAuthenticated ? <Navigate to={user?.role === 'admin' ? '/admin' : user?.role === 'teacher' ? '/teacher' : '/student'} replace /> : <LoginPage />} />
      <Route path="/login" element={isAuthenticated ? <Navigate to={user?.role === 'admin' ? '/admin' : user?.role === 'teacher' ? '/teacher' : '/student'} replace /> : <LoginPage />} />

      <Route element={<ProtectedRoute allowedRoles={['admin']} />}>
        <Route element={<AppShell role="admin" />}>
          <Route path="/admin" element={<AdminDashboard />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['teacher']} />}>
        <Route element={<AppShell role="teacher" />}>
          <Route path="/teacher" element={<TeacherDashboard />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['student']} />}>
        <Route element={<AppShell role="student" />}>
          <Route path="/student" element={<StudentDashboard />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'context').mkdir(exist_ok=True)
(frontend / 'src' / 'context' / 'AuthContext.jsx').write_text("""import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = async () => {
    const token = localStorage.getItem('accessToken')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    try {
      const { data } = await api.get('/auth/me/')
      setUser(data)
    } catch {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setUser(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUser()
  }, [])

  const value = useMemo(() => ({
    user,
    isAuthenticated: !!user,
    loading,
    setUser,
    refreshUser: loadUser,
    logout: () => {
      localStorage.removeItem('accessToken')
      localStorage.removeItem('refreshToken')
      setUser(null)
    },
  }), [user, loading])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
""", encoding='utf-8')
(frontend / 'src' / 'services').mkdir(exist_ok=True)
(frontend / 'src' / 'services' / 'api.js').write_text("""import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api
""", encoding='utf-8')
(frontend / 'src' / 'routes').mkdir(exist_ok=True)
(frontend / 'src' / 'routes' / 'ProtectedRoute.jsx').write_text("""import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function ProtectedRoute({ allowedRoles }) {
  const { user, isAuthenticated, loading } = useAuth()

  if (loading) return <div className="loading-screen">Chargement...</div>
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    return <Navigate to={user?.role === 'admin' ? '/admin' : user?.role === 'teacher' ? '/teacher' : '/student'} replace />
  }

  return <Outlet />
}
""", encoding='utf-8')
(frontend / 'src' / 'layouts').mkdir(exist_ok=True)
(frontend / 'src' / 'layouts' / 'AppShell.jsx').write_text("""import { Outlet, useNavigate } from 'react-router-dom'
import { GraduationCap, LogOut, Menu } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

export default function AppShell({ role }) {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-row">
          <div className="brand-mark"><GraduationCap size={20} /></div>
          <div>
            <strong>Université</strong>
            <small>{role === 'admin' ? 'Administration' : role === 'teacher' ? 'Professeur' : 'Étudiant'}</small>
          </div>
        </div>
        <nav className="nav-menu">
          <button className="nav-link active">Tableau de bord</button>
          <button className="nav-link">Utilisateurs</button>
          <button className="nav-link">Cours</button>
          <button className="nav-link">Documents</button>
        </nav>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <button className="icon-button mobile-only"><Menu size={18} /></button>
            <h1>Bienvenue, {user?.first_name || 'Utilisateur'}</h1>
          </div>
          <div className="topbar-actions">
            <span>{user?.email}</span>
            <button className="logout-button" onClick={handleLogout}><LogOut size={16} /> Déconnexion</button>
          </div>
        </header>

        <div className="content-area">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'pages').mkdir(exist_ok=True)
(frontend / 'src' / 'pages' / 'LoginPage.jsx').write_text("""import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Eye, EyeOff, Lock, Mail } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setUser } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const { data } = await api.post('/auth/login/', form)
      localStorage.setItem('accessToken', data.access)
      localStorage.setItem('refreshToken', data.refresh)
      setUser(data.user)
      const role = data.user.role
      navigate(role === 'admin' ? '/admin' : role === 'teacher' ? '/teacher' : '/student', { replace: true })
    } catch (err) {
      setError(err?.response?.data?.non_field_errors?.[0] || 'Erreur d\'authentification.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-brand">
          <div className="brand-icon">U</div>
          <div>
            <h2>Université de Strasbourg</h2>
            <p>Portail académique</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <div className="input-group">
            <label>Adresse e-mail</label>
            <div className="input-wrap">
              <Mail size={16} />
              <input type="email" name="email" value={form.email} onChange={handleChange} placeholder="prenom.nom@unistra.fr" required />
            </div>
          </div>

          <div className="input-group">
            <label>Mot de passe</label>
            <div className="input-wrap">
              <Lock size={16} />
              <input type={showPassword ? 'text' : 'password'} name="password" value={form.password} onChange={handleChange} placeholder="Votre mot de passe" required />
              <button type="button" className="password-toggle" onClick={() => setShowPassword(!showPassword)}>
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          {error ? <div className="error-message">{error}</div> : null}
          <button type="submit" className="primary-button" disabled={loading}>
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>
      </div>
    </div>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'pages' / 'admin').mkdir(exist_ok=True)
(frontend / 'src' / 'pages' / 'admin' / 'AdminDashboard.jsx').write_text("""export default function AdminDashboard() {
  return (
    <div className="dashboard-grid">
      <div className="stat-card blue">
        <span>Étudiants</span>
        <strong>1 248</strong>
      </div>
      <div className="stat-card gold">
        <span>Professeurs</span>
        <strong>98</strong>
      </div>
      <div className="stat-card slate">
        <span>Filières</span>
        <strong>26</strong>
      </div>
      <div className="stat-card gray">
        <span>Cours</span>
        <strong>340</strong>
      </div>
    </div>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'pages' / 'teacher').mkdir(exist_ok=True)
(frontend / 'src' / 'pages' / 'teacher' / 'TeacherDashboard.jsx').write_text("""export default function TeacherDashboard() {
  return (
    <div className="dashboard-grid">
      <div className="stat-card blue">
        <span>Matières</span>
        <strong>6</strong>
      </div>
      <div className="stat-card gold">
        <span>Étudiants</span>
        <strong>162</strong>
      </div>
      <div className="stat-card slate">
        <span>Cours publiés</span>
        <strong>12</strong>
      </div>
    </div>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'pages' / 'student').mkdir(exist_ok=True)
(frontend / 'src' / 'pages' / 'student' / 'StudentDashboard.jsx').write_text("""export default function StudentDashboard() {
  return (
    <div className="dashboard-grid">
      <div className="stat-card blue">
        <span>Matières</span>
        <strong>7</strong>
      </div>
      <div className="stat-card gold">
        <span>Cours</span>
        <strong>14</strong>
      </div>
      <div className="stat-card slate">
        <span>Documents</span>
        <strong>23</strong>
      </div>
    </div>
  )
}
""", encoding='utf-8')
(frontend / 'src' / 'styles').mkdir(exist_ok=True)
(frontend / 'src' / 'styles' / 'global.css').write_text("""* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Inter, 'Segoe UI', sans-serif;
  background: #f3f6fb;
  color: #1d2a39;
}
button, input {
  font: inherit;
}
#root {
  min-height: 100vh;
}
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  padding: 24px;
}
.login-card {
  width: min(460px, 100%);
  background: rgba(255, 255, 255, 0.97);
  border-radius: 20px;
  box-shadow: 0 22px 60px rgba(15, 23, 42, 0.25);
  padding: 32px;
}
.login-brand {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 28px;
}
.brand-icon {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  background: linear-gradient(135deg, #1e3a8a, #0f172a);
  color: white;
  display: grid;
  place-items: center;
  font-size: 1.8rem;
  font-weight: 700;
}
.login-brand h2 {
  margin: 0;
  font-size: 1.5rem;
}
.login-brand p {
  margin: 4px 0 0;
  color: #64748b;
}
.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.input-group label {
  font-weight: 600;
  color: #334155;
}
.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #f8fafc;
  border: 1px solid #dfe7f1;
  border-radius: 12px;
  padding: 0 14px;
}
.input-wrap input {
  border: none;
  background: transparent;
  height: 48px;
  width: 100%;
  outline: none;
  color: #0f172a;
}
.password-toggle {
  background: transparent;
  border: none;
  color: #475569;
  cursor: pointer;
}
.primary-button {
  background: linear-gradient(135deg, #1d4ed8, #0f172a);
  color: white;
  border: none;
  border-radius: 12px;
  min-height: 48px;
  font-weight: 700;
  letter-spacing: 0.02em;
  cursor: pointer;
}
.error-message {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  border-radius: 10px;
  padding: 10px 12px;
}
.app-shell {
  display: flex;
  min-height: 100vh;
  background: #eef4ff;
}
.sidebar {
  width: 260px;
  background: #0f172a;
  color: white;
  padding: 24px 18px;
}
.brand-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 30px;
  padding: 10px 8px;
}
.brand-mark {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #d4af37, #f5d77a);
  color: #0f172a;
}
.brand-row strong, .brand-row small { display: block; }
.brand-row small { opacity: 0.7; }
.nav-menu {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.nav-link {
  padding: 12px 14px;
  border: none;
  border-radius: 12px;
  background: transparent;
  color: #dfeaf9;
  text-align: left;
  cursor: pointer;
}
.nav-link.active {
  background: rgba(255,255,255,0.08);
}
.main-panel {
  flex: 1;
  padding: 24px;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 18px 20px;
  margin-bottom: 24px;
}
.topbar h1 {
  margin: 0;
  font-size: 1.7rem;
}
.topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.logout-button, .icon-button {
  border: 1px solid #dbe2ee;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
}
.content-area {
  min-height: 300px;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 18px;
}
.stat-card {
  border-radius: 18px;
  padding: 24px;
  color: white;
  min-height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.stat-card.blue { background: linear-gradient(135deg, #2563eb, #1d4ed8); }
.stat-card.gold { background: linear-gradient(135deg, #d4af37, #b68a20); }
.stat-card.slate { background: linear-gradient(135deg, #334155, #0f172a); }
.stat-card.gray { background: linear-gradient(135deg, #64748b, #475569); }
.stat-card span { font-size: 0.92rem; opacity: 0.9; }
.stat-card strong { font-size: 2.1rem; }
.loading-screen {
  min-height: 100vh;
  display: grid;
  place-items: center;
  font-weight: 600;
  color: #1e293b;
}
.mobile-only { display: none; }
@media (max-width: 900px) {
  .app-shell { flex-direction: column; }
  .sidebar { width: 100%; }
  .mobile-only { display: inline-flex; }
  .topbar { flex-direction: column; align-items: flex-start; gap: 12px; }
}
""", encoding='utf-8')

print('Project files created successfully')
