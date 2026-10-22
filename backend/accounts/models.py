from django.contrib.auth.models import AbstractUser
from django.db import models

from .managers import UserManager


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    matricule = models.CharField(max_length=40, unique=True, null=True, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    is_approved = models.BooleanField(default=True)
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


class AdminAuditLog(models.Model):
    actor = models.ForeignKey(
        User,
        related_name='admin_audit_logs',
        on_delete=models.SET_NULL,
        null=True,
    )
    action = models.CharField(max_length=40)
    resource_type = models.CharField(max_length=80)
    resource_id = models.CharField(max_length=80, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.action}: {self.resource_type} {self.resource_id}'
