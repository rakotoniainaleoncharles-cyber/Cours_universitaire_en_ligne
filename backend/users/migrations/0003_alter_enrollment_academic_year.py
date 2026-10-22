from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('users', '0002_alter_enrollment_unique_together_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='enrollment',
            name='academic_year',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='enrollments',
                to='academics.academicyear',
            ),
        ),
    ]
