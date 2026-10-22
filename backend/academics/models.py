from django.conf import settings
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
    faculty = models.ForeignKey(
        'Faculty',
        related_name='levels',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.name


class AcademicYear(models.Model):
    name = models.CharField(max_length=50, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

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
