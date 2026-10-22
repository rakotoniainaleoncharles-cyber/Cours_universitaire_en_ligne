from django.db import migrations


def preserve_published_content(apps, schema_editor):
    Course = apps.get_model('courses', 'Course')
    Lesson = apps.get_model('courses', 'Lesson')
    Course.objects.filter(published_at__isnull=False).update(status='published')
    Lesson.objects.filter(published_at__isnull=False).update(status='published')


class Migration(migrations.Migration):
    dependencies = [
        ('courses', '0002_assignment_alter_lesson_options_course_objectives_and_more'),
    ]

    operations = [
        migrations.RunPython(preserve_published_content, migrations.RunPython.noop),
    ]
