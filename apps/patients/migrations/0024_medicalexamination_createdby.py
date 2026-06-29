import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0023_medicalexamination'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='medicalexamination',
            name='doctor',
        ),
        migrations.AddField(
            model_name='medicalexamination',
            name='created_by',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='medical_examinations',
                to=settings.AUTH_USER_MODEL,
                verbose_name="Qo'shgan foydalanuvchi",
            ),
        ),
    ]
