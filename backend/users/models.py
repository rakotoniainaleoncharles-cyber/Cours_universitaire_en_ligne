from django.conf import settings
from django.db import models

from academics.models import Subject


class Enrollment(models.Model):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        INACTIVE = 'inactive', 'Inactive'

    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='enrollments', on_delete=models.CASCADE)
    subject = models.ForeignKey(Subject, related_name='enrollments', on_delete=models.CASCADE)
    academic_year = models.ForeignKey(
        'academics.AcademicYear',
        related_name='enrollments',
        on_delete=models.PROTECT,
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'subject', 'academic_year'],
                name='unique_student_subject_academic_year',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.academic_year_id is None and self.subject_id:
            self.academic_year_id = Subject.objects.values_list(
                'academic_year_id',
                flat=True,
            ).get(pk=self.subject_id)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.student.email} -> {self.subject.name}'
