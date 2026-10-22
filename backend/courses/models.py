from django.conf import settings
from django.db import models
from django.utils import timezone

from academics.models import Subject


class Course(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        PUBLISHED = 'published', 'Publié'

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    description = models.TextField()
    objectives = models.TextField(blank=True)
    subject = models.ForeignKey(Subject, related_name='courses', on_delete=models.CASCADE)
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='courses', on_delete=models.CASCADE)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        elif self.status == self.Status.DRAFT:
            self.published_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Lesson(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        PUBLISHED = 'published', 'Publié'

    course = models.ForeignKey(Course, related_name='lessons', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['order', 'id']

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        elif self.status == self.Status.DRAFT:
            self.published_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class Announcement(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Brouillon'
        PUBLISHED = 'published', 'Publié'

    course = models.ForeignKey(Course, related_name='announcements', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)
    published_at = models.DateTimeField(blank=True, null=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='modified_announcements',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and self.published_at is None:
            self.published_at = timezone.now()
        elif self.status == self.Status.DRAFT:
            self.published_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


class SocialPost(models.Model):
    class Kind(models.TextChoices):
        ADMIN = 'admin', 'Publication'
        TEACHER = 'teacher', 'Professeur'
        COURSE = 'course', 'Cours'
        SUBJECT = 'subject', 'Matière'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name='social_posts',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.ADMIN)
    title = models.CharField(max_length=200)
    content = models.TextField()
    image = models.ImageField(upload_to='social-posts/%Y/%m/%d/', blank=True)
    video = models.FileField(upload_to='social-posts/videos/%Y/%m/%d/', blank=True)
    course = models.ForeignKey(
        Course,
        related_name='social_posts',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    subject = models.ForeignKey(
        Subject,
        related_name='social_posts',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.title


class SocialPostLike(models.Model):
    post = models.ForeignKey(SocialPost, related_name='likes', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='social_post_likes', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_social_post_like'),
        ]


class SocialPostComment(models.Model):
    post = models.ForeignKey(SocialPost, related_name='comments', on_delete=models.CASCADE)
    parent_comment = models.ForeignKey(
        'self',
        related_name='replies',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='social_post_comments', on_delete=models.CASCADE)
    content = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']


class LessonProgress(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='lesson_progress', on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, related_name='student_progress', on_delete=models.CASCADE)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_accessed_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_accessed_at']
        constraints = [
            models.UniqueConstraint(fields=['student', 'lesson'], name='unique_student_lesson_progress'),
        ]


class Material(models.Model):
    course = models.ForeignKey(Course, related_name='materials', on_delete=models.CASCADE)
    lesson = models.ForeignKey(
        Lesson,
        related_name='materials',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/%Y/%m/%d/')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='materials', on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Assignment(models.Model):
    course = models.ForeignKey(Course, related_name='assignments', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    instructions = models.TextField()
    due_at = models.DateTimeField(blank=True, null=True)
    reference_file = models.FileField(upload_to='assignments/reference/%Y/%m/%d/', blank=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['due_at', '-created_at']

    def __str__(self):
        return self.title


class Submission(models.Model):
    assignment = models.ForeignKey(Assignment, related_name='submissions', on_delete=models.CASCADE)
    student = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='submissions', on_delete=models.CASCADE)
    file = models.FileField(upload_to='assignments/submissions/%Y/%m/%d/')
    corrected_file = models.FileField(upload_to='assignments/corrections/%Y/%m/%d/', blank=True)
    comment = models.TextField(blank=True)
    grade = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-submitted_at']
        constraints = [
            models.UniqueConstraint(fields=['assignment', 'student'], name='unique_assignment_submission'),
        ]

    @property
    def is_graded(self):
        return self.graded_at is not None

    def mark_graded(self):
        self.graded_at = timezone.now()

    def __str__(self):
        return f'{self.assignment.title} - {self.student.email}'
