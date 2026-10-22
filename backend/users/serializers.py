from rest_framework import serializers

from academics.models import AcademicYear
from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_email = serializers.EmailField(source='student.email', read_only=True)
    student_matricule = serializers.CharField(source='student.matricule', read_only=True, allow_null=True)
    subject_name = serializers.CharField(source='subject.name', read_only=True)
    subject_code = serializers.CharField(source='subject.code', read_only=True)
    academic_year = serializers.PrimaryKeyRelatedField(queryset=AcademicYear.objects.all(), required=False)
    academic_year_name = serializers.CharField(source='academic_year.name', read_only=True)
    faculty_name = serializers.CharField(source='subject.faculty.name', read_only=True)
    faculty_id = serializers.IntegerField(source='subject.faculty_id', read_only=True)
    level_name = serializers.CharField(source='subject.level.name', read_only=True)
    level_id = serializers.IntegerField(source='subject.level_id', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'student_name', 'student_email', 'student_matricule', 'subject', 'subject_name',
            'subject_code', 'faculty_name', 'faculty_id', 'level_name', 'level_id', 'academic_year', 'academic_year_name',
            'teacher_name', 'status', 'enrolled_at',
        ]
        read_only_fields = ['id', 'enrolled_at']
        validators = []

    def validate_student(self, student):
        if not student.is_student:
            raise serializers.ValidationError('Seul un compte étudiant peut être inscrit.')
        return student

    def validate(self, attrs):
        subject = attrs.get('subject', getattr(self.instance, 'subject', None))
        student = attrs.get('student', getattr(self.instance, 'student', None))
        year = attrs.get('academic_year', getattr(self.instance, 'academic_year', None))
        enrollment_status = attrs.get('status', getattr(self.instance, 'status', Enrollment.Status.ACTIVE))
        if student and not student.is_active and enrollment_status == Enrollment.Status.ACTIVE:
            raise serializers.ValidationError({'student': 'Un compte étudiant désactivé ne peut pas avoir une inscription active.'})
        if subject and year is None:
            year = subject.academic_year
            attrs['academic_year'] = year
        if subject and year and subject.academic_year_id != year.id and (
            self.instance is None or 'subject' in attrs or 'academic_year' in attrs
        ):
            raise serializers.ValidationError({'academic_year': 'L’année doit correspondre à celle de la matière choisie.'})
        if student and subject and year and Enrollment.objects.filter(
            student=student, subject=subject, academic_year=year,
        ).exclude(pk=getattr(self.instance, 'pk', None)).exists():
            raise serializers.ValidationError('Cet étudiant est déjà inscrit à cette matière pour cette année.')
        request = self.context.get('request')
        if request and request.user.is_teacher and subject and subject.teacher_id != request.user.id:
            raise serializers.ValidationError({'subject': 'Vous ne pouvez pas consulter cette inscription.'})
        return attrs

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.email

    def get_teacher_name(self, obj):
        teacher = obj.subject.teacher
        return (teacher.get_full_name() or teacher.email) if teacher else None
