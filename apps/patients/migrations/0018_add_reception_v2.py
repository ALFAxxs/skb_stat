import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0017_alter_patientcard_visit_type'),
    ]

    operations = [
        # --- PatientCard yangi maydonlar ---
        migrations.AddField(
            model_name='patientcard',
            name='room_number',
            field=models.CharField(blank=True, max_length=20, verbose_name='Xona raqami'),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='mobility_type',

            field=models.CharField(
                blank=True, max_length=15,
                choices=[('walking', 'Yura oladi'), ('wheelchair', 'Aravachada'), ('stretcher', 'Zambilda')],
                verbose_name='Harakatlanish turi',
            ),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='transport_type',
            field=models.CharField(
                blank=True, max_length=15,
                choices=[('ambulance', 'Tez tibbiy yordam'), ('own', "O'z transporti"), ('police', 'Politsiya'), ('other', 'Boshqa')],
                verbose_name='Transport turi',
            ),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='blood_group',
            field=models.CharField(
                blank=True, max_length=5,
                choices=[('I', 'I (0)'), ('II', 'II (A)'), ('III', 'III (B)'), ('IV', 'IV (AB)')],
                verbose_name='Qon guruhi',
            ),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='rh_factor',
            field=models.CharField(
                blank=True, max_length=5,
                choices=[('pos', 'Rh+ (musbat)'), ('neg', 'Rh− (manfiy)')],
                verbose_name='Rezus-faktor',
            ),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='drug_allergy',
            field=models.TextField(blank=True, verbose_name='Dorilarga allergiya'),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='height_cm',
            field=models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="Bo'yi (sm)"),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='weight_kg',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True, verbose_name='Vazni (kg)'),
        ),
        migrations.AddField(
            model_name='patientcard',
            name='body_temperature',
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=4, null=True, verbose_name='Harorat (°C)'),
        ),

        # --- InitialExamination ---
        migrations.CreateModel(
            name='InitialExamination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('complaints',                models.TextField(blank=True, verbose_name='Shikoyatlar')),
                ('anamnesis_morbi',           models.TextField(blank=True, verbose_name='Kasallik tarixi (Anamnesis morbi)')),
                ('anamnesis_vitae',           models.TextField(blank=True, verbose_name='Hayot tarixi (Anamnesis vitae)')),
                ('status_localis',            models.TextField(blank=True, verbose_name='Mahalliy holat (Status localis)')),
                ('epidemiological_anamnesis', models.TextField(blank=True, verbose_name='Epidemiologik anamnez')),
                ('status_praesens',           models.TextField(blank=True, verbose_name='Hozirgi holat (Status praesens)')),
                ('allergy_anamnesis',         models.TextField(blank=True, verbose_name='Allergologik anamnez')),
                ('neurological_status',       models.TextField(blank=True, verbose_name='Nevrologik holat')),
                ('lab_investigations',        models.TextField(blank=True, verbose_name='Laboratoriya tekshiruvlari')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient_card', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='initial_examination',
                    to='patients.patientcard',
                )),
            ],
            options={'verbose_name': "Boshlang'ich ko'rik", 'verbose_name_plural': "Boshlang'ich ko'riklar"},
        ),

        # --- EpisodeDiagnosis ---
        migrations.CreateModel(
            name='EpisodeDiagnosis',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('diagnosis_type', models.CharField(
                    choices=[('preliminary', 'Dastlabki'), ('final', 'Yakuniy')],
                    default='preliminary', max_length=15, verbose_name='Tashxis turi',
                )),
                ('diagnosis_role', models.CharField(
                    choices=[('main', 'Asosiy'), ('comorbidity', 'Hamroh kasallik'), ('complication', 'Asorat'), ('background', 'Fon kasalligi'), ('competitive', 'Raqobatdosh')],
                    default='main', max_length=15, verbose_name='Tashxis roli',
                )),
                ('clinical_text', models.TextField(blank=True, verbose_name='Klinik matn')),
                ('sort_order',    models.PositiveSmallIntegerField(default=0)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('patient_card', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='episode_diagnoses',
                    to='patients.patientcard',
                )),
                ('icd10_code', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='patients.icd10code',
                    verbose_name='MKB-10 kodi',
                )),
            ],
            options={'verbose_name': 'Epizod tashxisi', 'verbose_name_plural': 'Epizod tashxislari', 'ordering': ['sort_order', 'created_at']},
        ),
    ]
