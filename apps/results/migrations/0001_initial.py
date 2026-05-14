from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('services', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ResultTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=200, verbose_name='Shablon nomi')),
                ('category', models.CharField(
                    choices=[
                        ('lab', '🔬 Laboratoriya'),
                        ('radiology', '🩻 Rentgen / UZI / MRT'),
                        ('consultation', '👨\u200d⚕️ Konsultatsiya'),
                        ('procedure', '💉 Muolaja'),
                        ('other', '📄 Boshqa'),
                    ],
                    default='other', max_length=20, verbose_name='Kategoriya'
                )),
                ('content', models.TextField(verbose_name='Shablon HTML kontent')),
                ('description', models.CharField(blank=True, max_length=300, verbose_name='Tavsif')),
                ('is_active', models.BooleanField(default=True, verbose_name='Faol')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='users.customuser', verbose_name='Yaratuvchi'
                )),
            ],
            options={'verbose_name': 'Natija shabloni', 'verbose_name_plural': 'Natija shablonlari', 'ordering': ['category', 'name']},
        ),
        migrations.CreateModel(
            name='ServiceResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('content', models.TextField(verbose_name='Natija HTML kontent')),
                ('status', models.CharField(
                    choices=[('draft', '✏️ Qoralama'), ('completed', '✅ Yakunlangan')],
                    default='draft', max_length=20, verbose_name='Holat'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient_service', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='result', to='services.patientservice',
                    verbose_name='Xizmat'
                )),
                ('template', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='results.resulttemplate', verbose_name='Shablon'
                )),
                ('created_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='results_created',
                    to='users.customuser', verbose_name='Kim kiritdi'
                )),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='results_updated',
                    to='users.customuser', verbose_name='Kim tahrirladi'
                )),
            ],
            options={'verbose_name': 'Xizmat natijasi', 'verbose_name_plural': 'Xizmat natijalari', 'ordering': ['-created_at']},
        ),
    ]
