from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0024_medicalexamination_createdby'),
    ]

    operations = [
        # MedicalExamination — yangi maydonlar
        migrations.AddField(
            model_name='medicalexamination',
            name='department_head_name',
            field=models.CharField(blank=True, max_length=255, verbose_name="Bo'lim mudiri"),
        ),
        migrations.AddField(
            model_name='medicalexamination',
            name='specialist_consultations',
            field=models.TextField(blank=True, verbose_name='Turdosh mutaxassislar maslahatlari'),
        ),
        migrations.AddField(
            model_name='medicalexamination',
            name='drug_justification',
            field=models.TextField(blank=True, verbose_name='Dori vositalari uchun asoslar'),
        ),
        # EpisodeDiagnosis — disease_course
        migrations.AddField(
            model_name='episodediagnosis',
            name='disease_course',
            field=models.CharField(
                blank=True, max_length=20,
                choices=[
                    ('', 'Belgilanmagan'),
                    ('acute', "O'tkir"),
                    ('subacute', "O'tkir osti"),
                    ('chronic_first', "Hayotda birinchi marta surunkali"),
                    ('chronic_year', "Bu yil birinchi marta surunkali"),
                    ('chronic', 'Surunkali'),
                ],
                verbose_name='Kasallikning kechishi',
            ),
        ),
        migrations.AlterField(
            model_name='episodediagnosis',
            name='clinical_text',
            field=models.TextField(blank=True, max_length=3000, verbose_name='Klinik matn'),
        ),
    ]
