import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0022_merge_0018_0021'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalExamination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('examination_type', models.CharField(
                    max_length=30,
                    choices=[
                        ('initial',         "Dastlabki ko'rik"),
                        ('ward',            "Bo'limda tekshirish"),
                        ('daily',           'Tekshirish kundaligi'),
                        ('specialist',      'Maxsus mutaxassis tekshirishi'),
                        ('clinical_basis',  'Klinik tashxisning asoslanishi'),
                        ('stage_epicrisis', 'Bosqichli epikriz'),
                        ('discharge',       'Chiqarish epikrizi'),
                        ('consilium',       'Statsionar sharoitidagi Konsilium'),
                        ('anesthesia',      "Anesteziologning jarrohlik amaliyotidan oldingi ko'rigi"),
                    ],
                    verbose_name="Ko'rik turi",
                )),
                ('examination_datetime',  models.DateTimeField(blank=True, null=True, verbose_name="Ko'rik vaqti")),
                ('complaints',            models.TextField(blank=True, verbose_name='Shikoyatlar')),
                ('anamnesis_morbi',       models.TextField(blank=True, verbose_name='Kasallik tarixi')),
                ('anamnesis_vitae',       models.TextField(blank=True, verbose_name='Hayot tarixi')),
                ('status_localis',        models.TextField(blank=True, verbose_name='Mahalliy holat')),
                ('epidemiological_anamnesis', models.TextField(blank=True, verbose_name='Epidemiologik anamnez')),
                ('status_praesens',       models.TextField(blank=True, verbose_name='Hozirgi holat')),
                ('allergy_anamnesis',     models.TextField(blank=True, verbose_name='Allergologik anamnez')),
                ('neurological_status',   models.TextField(blank=True, verbose_name='Nevrologik holat')),
                ('lab_investigations',    models.TextField(blank=True, verbose_name='Lab tekshiruvlari')),
                ('conclusion',            models.TextField(blank=True, verbose_name='Xulosa / Tavsiya')),
                ('created_at',            models.DateTimeField(auto_now_add=True)),
                ('updated_at',            models.DateTimeField(auto_now=True)),
                ('patient_card', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='medical_examinations',
                    to='patients.patientcard',
                )),
                ('doctor', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='patients.doctor',
                    verbose_name='Shifokor',
                )),
            ],
            options={
                'verbose_name': "Tibbiy ko'rik",
                'verbose_name_plural': "Tibbiy ko'riklar",
                'ordering': ['-examination_datetime', '-created_at'],
            },
        ),
    ]
