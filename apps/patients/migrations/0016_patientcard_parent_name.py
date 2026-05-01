from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [
        ('patients', '0015_patientcard_visit_type'),
    ]
    operations = [
        migrations.AddField(
            model_name='patientcard',
            name='parent_name',
            field=models.CharField(blank=True, max_length=255, verbose_name='Ota-ona / Vasiy ismi'),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='parent_jshshir',
            field=models.CharField(blank=True, max_length=14, verbose_name='Ota-ona JSHSHIR'),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='parent_workplace_org',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='children_patients',
                to='patients.organization',
                verbose_name='Ota-ona ish joyi'
            ),
        ),
    ]
