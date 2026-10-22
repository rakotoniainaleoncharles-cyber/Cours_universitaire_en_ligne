import re
import os

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers

from academics.models import AcademicYear, Faculty, Subject
from users.models import Enrollment
from .models import User

AVATAR_FORMAT_EXTENSIONS = {
    'JPEG': {'.jpg', '.jpeg'},
    'PNG': {'.png'},
    'WEBP': {'.webp'},
}


def validate_phone_number(value):
    if value and re.fullmatch(r'[0-9]{10}', value) is None:
        raise serializers.ValidationError('Le numéro de téléphone doit contenir exactement 10 chiffres.')
    return value


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(choices=[('admin', 'Administrateur'), ('teacher', 'Professeur'), ('student', 'Étudiant')], read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True, write_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'matricule', 'phone', 'role', 'avatar', 'avatar_url', 'is_active', 'is_approved', 'created_at', 'updated_at']
        read_only_fields = ['id', 'matricule', 'phone', 'role', 'is_active', 'is_approved', 'created_at', 'updated_at']

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return ''
        from django.urls import reverse

        return reverse('user-avatar', kwargs={'pk': obj.pk})

    def validate_avatar(self, avatar):
        if not avatar:
            return avatar
        try:
            with Image.open(avatar) as image:
                image_format = image.format
                if image_format not in AVATAR_FORMAT_EXTENSIONS:
                    raise serializers.ValidationError('La photo doit être au format JPEG, PNG ou WebP.')
                extension = os.path.splitext(avatar.name)[1].lower()
                if extension not in AVATAR_FORMAT_EXTENSIONS[image_format]:
                    raise serializers.ValidationError('L’extension ne correspond pas au format de la photo.')
                if image.width * image.height > 20_000_000:
                    raise serializers.ValidationError('La résolution de la photo est trop élevée.')
                image.verify()
        except UnidentifiedImageError as error:
            raise serializers.ValidationError('Le fichier envoyé n’est pas une image valide.') from error
        except (OSError, SyntaxError, Image.DecompressionBombError) as error:
            raise serializers.ValidationError('Le fichier image est invalide ou trop volumineux.') from error
        avatar.seek(0)
        return avatar

    def update(self, instance, validated_data):
        previous_avatar = instance.avatar
        instance = super().update(instance, validated_data)
        if previous_avatar and previous_avatar.name != (instance.avatar.name if instance.avatar else None):
            previous_avatar.delete(save=False)
        return instance


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, required=False)
    role = serializers.ChoiceField(choices=[('teacher', 'Professeur'), ('student', 'Étudiant')])
    avatar = serializers.ImageField(required=False, allow_null=True, write_only=True)
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name', 'matricule', 'phone', 'role', 'avatar', 'avatar_url', 'is_active', 'is_approved', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_fields(self):
        fields = super().get_fields()
        fields['password'].required = self.instance is None
        fields['matricule'].required = False
        fields['matricule'].allow_blank = True
        fields['matricule'].allow_null = True
        fields['phone'].required = False
        fields['is_approved'].read_only = True
        if self.instance is not None and getattr(self.instance, 'is_admin', False):
            fields['role'].read_only = True
            fields['is_active'].read_only = True
        return fields

    def validate_password(self, value):
        validate_password(value, self.instance)
        return value

    def validate_matricule(self, value):
        return value or None

    def validate_phone(self, value):
        return validate_phone_number(value)

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return ''
        from django.urls import reverse

        return reverse('user-avatar', kwargs={'pk': obj.pk})

    def validate_avatar(self, avatar):
        return UserSerializer().validate_avatar(avatar)

    def create(self, validated_data):
        password = validated_data.pop('password')
        return User.objects.create_user(password=password, **validated_data)

    def update(self, instance, validated_data):
        if instance.is_admin and validated_data.get('is_active') is False:
            raise serializers.ValidationError({'is_active': 'Le compte administrateur unique ne peut pas être désactivé.'})
        if not instance.is_approved and validated_data.get('is_active') is True:
            instance.is_approved = True
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class _RegistrationFieldsSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=[('student', 'Étudiant'), ('teacher', 'Professeur')],
        required=False,
        default='student',
        write_only=True,
    )

    class Meta:
        model = User
        fields = ['email', 'password', 'first_name', 'last_name', 'role', 'phone']

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_phone(self, value):
        return validate_phone_number(value)

    def validate(self, attrs):
        if attrs.get('role', 'student') == 'student' and not attrs.get('phone', '').strip():
            raise serializers.ValidationError({'phone': 'Le numéro de téléphone est obligatoire pour une inscription étudiante.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.update(is_active=False, is_approved=False)
        return User.objects.create_user(password=password, **validated_data)


class RegisterSerializer(_RegistrationFieldsSerializer):
    faculty = serializers.PrimaryKeyRelatedField(
        queryset=Faculty.objects.all(),
        required=False,
        write_only=True,
    )
    subject_ids = serializers.PrimaryKeyRelatedField(
        queryset=Subject.objects.select_related('faculty', 'academic_year').all(),
        many=True,
        required=False,
        write_only=True,
    )

    class Meta(_RegistrationFieldsSerializer.Meta):
        fields = _RegistrationFieldsSerializer.Meta.fields + ['faculty', 'subject_ids']

    def validate(self, attrs):
        if attrs.get('role', 'student') != 'student':
            return attrs
        if not attrs.get('phone', '').strip():
            raise serializers.ValidationError({
                'phone': 'Le numéro de téléphone est obligatoire pour une inscription étudiante.',
            })
        faculty = attrs.get('faculty')
        subjects = attrs.get('subject_ids', [])
        if faculty is None:
            raise serializers.ValidationError({'faculty': 'Choisissez une filière.'})
        if not subjects:
            raise serializers.ValidationError({'subject_ids': 'Choisissez au moins une matière.'})
        if len({subject.pk for subject in subjects}) != len(subjects):
            raise serializers.ValidationError({
                'subject_ids': 'Une matière ne peut être sélectionnée qu’une seule fois.',
            })
        active_year = AcademicYear.objects.filter(is_active=True).first()
        if active_year is None:
            raise serializers.ValidationError({
                'faculty': 'Aucune année universitaire active ne permet les inscriptions actuellement.',
            })
        if any(
            subject.faculty_id != faculty.pk or subject.academic_year_id != active_year.pk
            for subject in subjects
        ):
            raise serializers.ValidationError({
                'subject_ids': 'Les matières choisies doivent appartenir à la filière sélectionnée et à l’année universitaire active.',
            })
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data.pop('faculty', None)
        subjects = validated_data.pop('subject_ids', [])
        validated_data.update(is_active=False, is_approved=False)
        user = User.objects.create_user(password=password, **validated_data)
        if user.role == 'student':
            Enrollment.objects.bulk_create([
                Enrollment(
                    student=user,
                    subject=subject,
                    academic_year=subject.academic_year,
                    status=Enrollment.Status.ACTIVE,
                )
                for subject in subjects
            ])
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs['email'], password=attrs['password'])
        if not user:
            raise serializers.ValidationError('Identifiants invalides.')
        if not user.is_active:
            if not user.is_approved:
                raise serializers.ValidationError('Votre inscription est en attente de validation par l’administration.')
            raise serializers.ValidationError('Ce compte est désactivé.')
        return {'user': user}


class PasswordResetSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_password(self, value):
        validate_password(value)
        return value
