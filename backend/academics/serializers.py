from rest_framework import serializers
from django.db import transaction

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

    def validate(self, attrs):
        start_date = attrs.get('start_date', getattr(self.instance, 'start_date', None))
        end_date = attrs.get('end_date', getattr(self.instance, 'end_date', None))
        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError({'end_date': 'La date de fin doit être postérieure à la date de début.'})
        return attrs

    def create(self, validated_data):
        with transaction.atomic():
            if validated_data.get('is_active'):
                AcademicYear.objects.select_for_update().filter(is_active=True).update(is_active=False)
            return super().create(validated_data)

    def update(self, instance, validated_data):
        with transaction.atomic():
            if validated_data.get('is_active', instance.is_active):
                AcademicYear.objects.select_for_update().filter(is_active=True).exclude(pk=instance.pk).update(is_active=False)
            return super().update(instance, validated_data)


class SubjectSerializer(serializers.ModelSerializer):
    faculty_name = serializers.CharField(source='faculty.name', read_only=True)
    level_name = serializers.CharField(source='level.name', read_only=True)
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ['id', 'code', 'name', 'description', 'faculty', 'faculty_name', 'level', 'level_name', 'academic_year', 'teacher', 'teacher_name']

    def validate_teacher(self, teacher):
        if teacher and not teacher.is_teacher:
            raise serializers.ValidationError('Seul un compte de professeur peut être affecté à une matière.')
        if teacher and not teacher.is_active:
            raise serializers.ValidationError('Un compte de professeur désactivé ne peut pas recevoir de matière.')
        return teacher

    def validate(self, attrs):
        faculty = attrs.get('faculty', getattr(self.instance, 'faculty', None))
        level = attrs.get('level', getattr(self.instance, 'level', None))
        if faculty and level and level.faculty_id and level.faculty_id != faculty.id:
            raise serializers.ValidationError({'level': 'Le niveau sélectionné n’appartient pas à la filière choisie.'})
        return attrs

    def get_teacher_name(self, obj):
        if obj.teacher:
            return obj.teacher.get_full_name() or obj.teacher.email
        return None
