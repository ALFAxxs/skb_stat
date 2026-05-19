# Generated migration for laboratory app

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('patients', '0001_initial'),
        ('services', '0006_servicepackage_servicepackageitem_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LabTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Shablon nomi')),
                ('category', models.CharField(
                    choices=[
                        ('general_blood', 'Umumiy qon tahlili'),
                        ('biochemistry', 'Biokimyo'),
                        ('urine', 'Siydik tahlili'),
                        ('coagulation', 'Koagulyatsiya'),
                        ('hormones', 'Gormonlar'),
                        ('immunology', 'Immunologiya'),
                        ('microbiology', 'Mikrobiologiya'),
                        ('serology', 'Serologiya'),
                        ('other', 'Boshqa'),
                    ],
                    default='other',
                    max_length=30,
                    verbose_name='Kategoriya'
                )),
                ('description', models.TextField(blank=True, verbose_name='Tavsifi')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faolmi')),
            ],
            options={
                'verbose_name': 'Lab shabloni',
                'verbose_name_plural': 'Lab shablonlari',
                'ordering': ['category', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LabParameterGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Guruh nomi')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='groups',
                    to='laboratory.labtemplate',
                    verbose_name='Shablon'
                )),
            ],
            options={
                'verbose_name': 'Parametr guruhi',
                'verbose_name_plural': 'Parametr guruhlari',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LabParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Nomi')),
                ('name_ru', models.CharField(blank=True, max_length=255, verbose_name='Nomi (ruscha)')),
                ('unit', models.CharField(blank=True, max_length=50, verbose_name="O'lchov birligi")),
                ('param_type', models.CharField(
                    choices=[
                        ('numeric', 'Raqamli'),
                        ('text', 'Matnli'),
                        ('select', 'Tanlov'),
                    ],
                    default='numeric',
                    max_length=10,
                    verbose_name='Parametr turi'
                )),
                ('normal_min', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor min")),
                ('normal_max', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor max")),
                ('critical_min', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name='Kritik min')),
                ('critical_max', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name='Kritik max')),
                ('normal_min_m', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor min (erkak)")),
                ('normal_max_m', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor max (erkak)")),
                ('normal_min_f', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor min (ayol)")),
                ('normal_max_f', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True, verbose_name="Me'yor max (ayol)")),
                ('select_options', models.JSONField(blank=True, default=list, verbose_name='Tanlov variantlari')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Tartib raqami')),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='parameters',
                    to='laboratory.labtemplate',
                    verbose_name='Shablon'
                )),
                ('group', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='parameters',
                    to='laboratory.labparametergroup',
                    verbose_name='Guruh'
                )),
            ],
            options={
                'verbose_name': 'Lab parametri',
                'verbose_name_plural': 'Lab parametrlari',
                'ordering': ['sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='LabResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('draft', 'Qoralama'),
                        ('done', 'Bajarildi'),
                        ('verified', 'Tasdiqlandi'),
                        ('printed', 'Chop etildi'),
                    ],
                    default='draft',
                    max_length=10,
                    verbose_name='Holati'
                )),
                ('conclusion', models.TextField(blank=True, verbose_name='Xulosa')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Yaratilgan vaqt')),
                ('printed_at', models.DateTimeField(blank=True, null=True, verbose_name='Chop etilgan vaqt')),
                ('patient_card', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='lab_results',
                    to='patients.patientcard',
                    verbose_name='Bemor kartasi'
                )),
                ('template', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='results',
                    to='laboratory.labtemplate',
                    verbose_name='Shablon'
                )),
                ('services', models.ManyToManyField(
                    blank=True,
                    related_name='lab_results',
                    to='services.patientservice',
                    verbose_name='Xizmatlar'
                )),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_lab_results',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Yaratgan'
                )),
                ('verified_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='verified_lab_results',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='Tasdiqlagan'
                )),
            ],
            options={
                'verbose_name': 'Lab natijasi',
                'verbose_name_plural': 'Lab natijalari',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='LabResultValue',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.CharField(blank=True, max_length=500, verbose_name='Qiymat')),
                ('value_status', models.CharField(
                    choices=[
                        ('normal', "Me'yor"),
                        ('high', 'Yuqori'),
                        ('low', 'Past'),
                        ('critical', 'Kritik'),
                        ('text', 'Matnli'),
                    ],
                    default='normal',
                    max_length=10,
                    verbose_name='Qiymat holati'
                )),
                ('comment', models.CharField(blank=True, max_length=500, verbose_name='Izoh')),
                ('result', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='values',
                    to='laboratory.labresult',
                    verbose_name='Natija'
                )),
                ('parameter', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='result_values',
                    to='laboratory.labparameter',
                    verbose_name='Parametr'
                )),
            ],
            options={
                'verbose_name': 'Natija qiymati',
                'verbose_name_plural': 'Natija qiymatlari',
                'unique_together': {('result', 'parameter')},
            },
        ),
    ]
