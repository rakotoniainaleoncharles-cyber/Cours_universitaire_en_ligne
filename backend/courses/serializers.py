import os
import zipfile

from PIL import Image, UnidentifiedImageError
from django.utils.text import slugify
from django.db.models import Q
from rest_framework import serializers

from .models import (
    Announcement,
    Assignment,
    Course,
    Lesson,
    Material,
    SocialPost,
    SocialPostComment,
    Submission,
)

MAX_UPLOAD_SIZE = 20 * 1024 * 1024
MAX_SOCIAL_IMAGE_SIZE = 5 * 1024 * 1024
MAX_SOCIAL_VIDEO_SIZE = 50 * 1024 * 1024
MAX_SOCIAL_IMAGE_PIXELS = 20_000_000
ALLOWED_SOCIAL_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_SOCIAL_VIDEO_EXTENSIONS = {'.mp4', '.webm'}
SOCIAL_IMAGE_EXTENSIONS = {
    'JPEG': {'.jpg', '.jpeg'},
    'PNG': {'.png'},
    'WEBP': {'.webp'},
}
ALLOWED_EXTENSIONS = {
    '.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx', '.zip', '.png', '.jpg', '.jpeg',
}
OLE_SIGNATURE = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'


def validate_uploaded_document(value):
    extension = os.path.splitext(value.name)[1].lower()
    if value.size > MAX_UPLOAD_SIZE:
        raise serializers.ValidationError('Le fichier ne doit pas dépasser 20 Mo.')
    if extension not in ALLOWED_EXTENSIONS:
        raise serializers.ValidationError('Type de fichier non autorisé.')

    signature = value.read(8)
    value.seek(0)
    if extension == '.pdf' and not signature.startswith(b'%PDF-'):
        raise serializers.ValidationError('Le contenu du fichier ne correspond pas à un PDF.')
    if extension in {'.doc', '.ppt', '.xls'} and not signature.startswith(OLE_SIGNATURE):
        raise serializers.ValidationError('Le contenu du fichier ne correspond pas à un document Office.')
    if extension == '.png' and not signature.startswith(b'\x89PNG\r\n\x1a\n'):
        raise serializers.ValidationError('Le contenu du fichier ne correspond pas à une image PNG.')
    if extension in {'.jpg', '.jpeg'} and not signature.startswith(b'\xff\xd8\xff'):
        raise serializers.ValidationError('Le contenu du fichier ne correspond pas à une image JPEG.')
    if extension in {'.docx', '.pptx', '.xlsx', '.zip'}:
        if not zipfile.is_zipfile(value):
            value.seek(0)
            raise serializers.ValidationError('Le fichier ZIP ou Office est invalide.')
        if extension != '.zip':
            value.seek(0)
            with zipfile.ZipFile(value) as archive:
                expected_part = {
                    '.docx': 'word/document.xml',
                    '.pptx': 'ppt/presentation.xml',
                    '.xlsx': 'xl/workbook.xml',
                }[extension]
                if expected_part not in archive.namelist():
                    value.seek(0)
                    raise serializers.ValidationError('Le contenu du fichier ne correspond pas à son extension.')
    value.seek(0)
    return value


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'course', 'title', 'description', 'content', 'order', 'status', 'published_at']
        read_only_fields = ['id', 'course', 'published_at']


class AnnouncementSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    teacher_avatar_url = serializers.SerializerMethodField()
    teacher_id = serializers.IntegerField(source='course.teacher_id', read_only=True)
    faculty_name = serializers.CharField(source='course.subject.faculty.name', read_only=True)
    modified_by_name = serializers.SerializerMethodField()
    modified_by_role = serializers.SerializerMethodField()

    class Meta:
        model = Announcement
        fields = [
            'id', 'course', 'course_title', 'teacher_name', 'teacher_avatar_url', 'teacher_id', 'faculty_name',
            'title', 'content', 'status', 'created_at', 'updated_at', 'published_at',
            'modified_by_name', 'modified_by_role',
        ]
        read_only_fields = [
            'id', 'course_title', 'teacher_name', 'teacher_avatar_url', 'teacher_id', 'faculty_name',
            'created_at', 'updated_at', 'published_at', 'modified_by_name', 'modified_by_role',
        ]

    def validate(self, attrs):
        request = self.context.get('request')
        course = attrs.get('course', getattr(self.instance, 'course', None))
        if request and request.user.is_teacher and course and course.teacher_id != request.user.id:
            raise serializers.ValidationError({'course': 'Ce cours ne vous appartient pas.'})
        return attrs

    def get_teacher_name(self, obj):
        teacher = obj.course.teacher
        return teacher.get_full_name() or teacher.email

    def get_teacher_avatar_url(self, obj):
        teacher = obj.course.teacher
        if not teacher.avatar:
            return ''
        from django.urls import reverse

        return reverse('user-avatar', kwargs={'pk': teacher.pk})

    def get_modified_by_name(self, obj):
        if not obj.modified_by:
            return ''
        return obj.modified_by.get_full_name() or obj.modified_by.email

    def get_modified_by_role(self, obj):
        return obj.modified_by.role if obj.modified_by else ''


class SocialPostCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.CharField(source='author.role', read_only=True)
    author_avatar_url = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = SocialPostComment
        fields = ['id', 'content', 'author_name', 'author_role', 'author_avatar_url', 'created_at', 'replies']
        read_only_fields = ['id', 'author_name', 'author_role', 'created_at']

    def get_replies(self, obj):
        return SocialPostCommentSerializer(
            obj.replies.all(),
            many=True,
            context=self.context,
        ).data

    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.email

    def get_author_avatar_url(self, obj):
        if not obj.author.avatar:
            return ''
        from django.urls import reverse

        return reverse('user-avatar', kwargs={'pk': obj.author_id})


class SocialPostSerializer(serializers.ModelSerializer):
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    author_avatar_url = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True, default='')
    subject_name = serializers.CharField(source='subject.name', read_only=True, default='')
    like_count = serializers.IntegerField(source='likes.count', read_only=True)
    liked_by_me = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = SocialPost
        fields = [
            'id', 'kind', 'title', 'content', 'author_name', 'author_role', 'author_avatar_url',
            'course_title', 'subject_name', 'image_url', 'video_url', 'like_count', 'liked_by_me',
            'comments', 'created_at',
        ]
        read_only_fields = [
            'id', 'kind', 'author_name', 'author_role', 'author_avatar_url', 'course_title', 'subject_name',
            'image_url', 'video_url', 'like_count', 'liked_by_me', 'comments', 'created_at',
        ]

    def get_author_name(self, obj):
        if not obj.author:
            return 'Administration'
        return obj.author.get_full_name() or obj.author.email

    def get_author_role(self, obj):
        return obj.author.role if obj.author else 'admin'

    def get_author_avatar_url(self, obj):
        if not obj.author or not obj.author.avatar:
            return ''
        from django.urls import reverse

        return reverse('user-avatar', kwargs={'pk': obj.author_id})

    def get_image_url(self, obj):
        if not obj.image:
            return ''
        from django.urls import reverse

        return reverse('social-post-image', kwargs={'pk': obj.pk})

    def get_video_url(self, obj):
        if not obj.video:
            return ''
        from django.urls import reverse

        return reverse('social-post-video', kwargs={'pk': obj.pk})

    def get_comments(self, obj):
        comments = [comment for comment in obj.comments.all() if comment.parent_comment_id is None]
        return SocialPostCommentSerializer(comments, many=True, context=self.context).data

    def get_liked_by_me(self, obj):
        request = self.context.get('request')
        return bool(
            request
            and request.user.is_authenticated
            and any(like.user_id == request.user.pk for like in obj.likes.all())
        )


class SocialPostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = SocialPost
        fields = ['title', 'content', 'image', 'video']

    def validate(self, attrs):
        if attrs.get('image') and attrs.get('video'):
            raise serializers.ValidationError('Ajoutez une image ou une vidéo, mais pas les deux.')
        return attrs

    def validate_image(self, image):
        if not image:
            return image
        if image.size > MAX_SOCIAL_IMAGE_SIZE:
            raise serializers.ValidationError('L’image ne doit pas dépasser 5 Mo.')

        try:
            with Image.open(image) as opened_image:
                actual_format = opened_image.format
                if actual_format not in ALLOWED_SOCIAL_IMAGE_FORMATS:
                    raise serializers.ValidationError('Seules les images JPEG, PNG et WebP sont autorisées.')
                extension = os.path.splitext(image.name)[1].lower()
                if extension not in SOCIAL_IMAGE_EXTENSIONS[actual_format]:
                    raise serializers.ValidationError('L’extension du fichier ne correspond pas au format de l’image.')
                if opened_image.width * opened_image.height > MAX_SOCIAL_IMAGE_PIXELS:
                    raise serializers.ValidationError('La résolution de l’image est trop élevée.')
                opened_image.verify()
        except UnidentifiedImageError as error:
            raise serializers.ValidationError('Le fichier envoyé n’est pas une image valide.') from error
        except (OSError, SyntaxError, Image.DecompressionBombError) as error:
            raise serializers.ValidationError('Le fichier image est invalide ou trop volumineux.') from error
        image.seek(0)
        return image

    def validate_video(self, video):
        if not video:
            return video
        if video.size > MAX_SOCIAL_VIDEO_SIZE:
            raise serializers.ValidationError('La vidéo ne doit pas dépasser 50 Mo.')

        extension = os.path.splitext(video.name)[1].lower()
        if extension not in ALLOWED_SOCIAL_VIDEO_EXTENSIONS:
            raise serializers.ValidationError('Seules les vidéos MP4 et WebM sont autorisées.')

        signature = video.read(12)
        video.seek(0)
        if extension == '.mp4' and (len(signature) < 8 or signature[4:8] != b'ftyp'):
            raise serializers.ValidationError('Le contenu du fichier ne correspond pas à une vidéo MP4.')
        if extension == '.webm' and not signature.startswith(b'\x1a\x45\xdf\xa3'):
            raise serializers.ValidationError('Le contenu du fichier ne correspond pas à une vidéo WebM.')
        return video


class MaterialSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    file_size = serializers.SerializerMethodField()
    lesson_title = serializers.CharField(source='lesson.title', read_only=True, default='')

    class Meta:
        model = Material
        fields = [
            'id', 'course', 'lesson', 'title', 'description', 'file', 'file_url',
            'file_name', 'file_size', 'lesson_title', 'uploaded_by', 'uploaded_at',
        ]
        read_only_fields = ['id', 'course', 'uploaded_by', 'uploaded_at', 'file_url', 'file_name', 'file_size']

    def get_file_url(self, obj):
        from django.urls import reverse

        url = reverse('material-download', kwargs={'pk': obj.pk})
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_file_name(self, obj):
        return os.path.basename(obj.file.name) if obj.file else ''

    def get_file_size(self, obj):
        return obj.file.size if obj.file else 0

    def validate_file(self, value):
        return validate_uploaded_document(value)

    def validate_lesson(self, lesson):
        course = self.context.get('course') or getattr(self.instance, 'course', None)
        if course and lesson and lesson.course_id != course.id:
            raise serializers.ValidationError('La leçon doit appartenir au même cours que le document.')
        return lesson


class AssignmentSerializer(serializers.ModelSerializer):
    reference_file = serializers.FileField(write_only=True, required=False)
    reference_file_url = serializers.SerializerMethodField()
    reference_file_name = serializers.SerializerMethodField()
    course_title = serializers.CharField(source='course.title', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    teacher_id = serializers.IntegerField(source='course.teacher_id', read_only=True)
    faculty_name = serializers.CharField(source='course.subject.faculty.name', read_only=True)
    submission_count = serializers.IntegerField(source='submissions.count', read_only=True)
    pending_count = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = [
            'id', 'course', 'course_title', 'teacher_name', 'teacher_id', 'faculty_name', 'title', 'instructions', 'due_at', 'reference_file', 'reference_file_url', 'reference_file_name',
            'is_published', 'created_at', 'updated_at', 'submission_count', 'pending_count',
        ]
        read_only_fields = ['id', 'course', 'course_title', 'created_at', 'updated_at', 'submission_count', 'pending_count', 'reference_file_url']

    def get_reference_file_url(self, obj):
        from django.urls import reverse

        if not obj.reference_file:
            return None
        url = reverse('assignment-reference-download', kwargs={'pk': obj.pk})
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_reference_file_name(self, obj):
        return os.path.basename(obj.reference_file.name) if obj.reference_file else ''

    def get_pending_count(self, obj):
        return obj.submissions.filter(graded_at__isnull=True).count()

    def get_teacher_name(self, obj):
        teacher = obj.course.teacher
        return teacher.get_full_name() or teacher.email

    def validate_reference_file(self, value):
        if value:
            return validate_uploaded_document(value)
        return value


class CourseSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    faculty_name = serializers.CharField(source='subject.faculty.name', read_only=True)
    level_name = serializers.CharField(source='subject.level.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()
    lessons = serializers.SerializerMethodField()
    materials = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()
    announcements = serializers.SerializerMethodField()
    slug = serializers.SlugField(required=False)

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'slug', 'description', 'objectives', 'subject', 'subject_name', 'subject_code',
            'faculty_name', 'level_name', 'teacher', 'teacher_name', 'status', 'created_at',
            'updated_at', 'published_at', 'lessons', 'materials', 'assignments', 'announcements',
        ]
        read_only_fields = ['id', 'teacher', 'created_at', 'updated_at', 'published_at', 'lessons', 'materials', 'assignments', 'announcements']

    def validate(self, attrs):
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        request = self.context.get('request')
        if request and request.user.is_teacher and subject and subject.teacher_id != request.user.id:
            raise serializers.ValidationError({'subject': 'Cette matière ne vous est pas attribuée.'})
        title = attrs.get('title', getattr(self.instance, 'title', ''))
        slug = attrs.get('slug') or slugify(title)
        if not slug:
            raise serializers.ValidationError({'title': 'Le titre doit permettre de générer un identifiant de cours.'})
        attrs['slug'] = slug
        return attrs

    def get_teacher_name(self, obj):
        return obj.teacher.get_full_name() or obj.teacher.email

    def get_lessons(self, obj):
        lessons = obj.lessons.all()
        request = self.context.get('request')
        if request and request.user.is_student:
            lessons = lessons.filter(status=Lesson.Status.PUBLISHED)
        return LessonSerializer(lessons, many=True, context=self.context).data

    def get_materials(self, obj):
        materials = obj.materials.all()
        request = self.context.get('request')
        if request and request.user.is_student:
            materials = materials.filter(
                Q(lesson__isnull=True) | Q(lesson__status=Lesson.Status.PUBLISHED)
            )
        return MaterialSerializer(materials, many=True, context=self.context).data

    def get_assignments(self, obj):
        assignments = obj.assignments.all()
        request = self.context.get('request')
        if request and request.user.is_student:
            assignments = assignments.filter(is_published=True)
        return AssignmentSerializer(assignments, many=True, context=self.context).data

    def get_announcements(self, obj):
        announcements = obj.announcements.all()
        request = self.context.get('request')
        if request and request.user.is_student:
            announcements = announcements.filter(status=Announcement.Status.PUBLISHED)
        return AnnouncementSerializer(announcements, many=True, context=self.context).data


class SubmissionSerializer(serializers.ModelSerializer):
    file = serializers.FileField(write_only=True, required=False)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    corrected_file = serializers.FileField(write_only=True, required=False)
    corrected_file_url = serializers.SerializerMethodField()
    corrected_file_name = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    assignment_title = serializers.CharField(source='assignment.title', read_only=True)
    course_title = serializers.CharField(source='assignment.course.title', read_only=True)
    student_email = serializers.EmailField(source='student.email', read_only=True)
    is_graded = serializers.BooleanField(read_only=True)

    class Meta:
        model = Submission
        fields = [
            'id', 'assignment', 'student', 'student_name', 'student_email',
            'assignment_title', 'course_title', 'file', 'file_url', 'file_name',
            'corrected_file', 'corrected_file_url', 'corrected_file_name',
            'comment', 'grade', 'feedback', 'submitted_at', 'graded_at', 'is_graded',
        ]
        read_only_fields = [
            'id', 'assignment', 'student', 'student_name', 'student_email', 'file_url', 'file_name',
            'corrected_file_url', 'corrected_file_name', 'submitted_at', 'graded_at', 'is_graded',
            'grade', 'feedback', 'corrected_file',
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if request and request.user.is_teacher:
            fields['file'].read_only = True
            fields['corrected_file'].read_only = False
            fields['grade'].read_only = False
            fields['feedback'].read_only = False
        return fields

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email

    def get_file_url(self, obj):
        from django.urls import reverse

        url = reverse('submission-download', kwargs={'pk': obj.pk})
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_file_name(self, obj):
        return os.path.basename(obj.file.name)

    def get_corrected_file_url(self, obj):
        if not obj.corrected_file:
            return None

        from django.urls import reverse

        url = reverse('submission-corrected-download', kwargs={'pk': obj.pk})
        request = self.context.get('request')
        return request.build_absolute_uri(url) if request else url

    def get_corrected_file_name(self, obj):
        return os.path.basename(obj.corrected_file.name) if obj.corrected_file else ''

    def validate_file(self, value):
        return validate_uploaded_document(value)

    def validate_corrected_file(self, value):
        return validate_uploaded_document(value)

    def validate_grade(self, value):
        if value is not None and not 0 <= value <= 20:
            raise serializers.ValidationError('La note doit être comprise entre 0 et 20.')
        return value

    def update(self, instance, validated_data):
        if 'grade' in validated_data or 'feedback' in validated_data or 'corrected_file' in validated_data:
            from django.utils import timezone

            instance.graded_at = timezone.now()
        return super().update(instance, validated_data)
