# apps/contracts/migrations/0001_initial.py

import uuid
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('patients', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Contract',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contract_number', models.CharField(max_length=30, unique=True, verbose_name='Shartnoma raqami')),
                ('contract_date', models.DateField(auto_now_add=True, verbose_name='Shartnoma sanasi')),
                ('contract_type', models.CharField(
                    choices=[('paid', 'Pullik'), ('non_resident', 'Norezident')],
                    max_length=20, verbose_name='Turi'
                )),
                ('status', models.CharField(
                    choices=[('draft', 'Loyiha'), ('active', 'Faol'), ('cancelled', 'Bekor qilingan')],
                    default='active', max_length=20, verbose_name='Holati'
                )),
                ('verify_token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('pdf_file', models.FileField(blank=True, null=True, upload_to='contracts/', verbose_name='PDF fayl')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('patient_card', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='contract',
                    to='patients.patientcard',
                    verbose_name='Bemor kartasi'
                )),
            ],
            options={
                'verbose_name': 'Shartnoma',
                'verbose_name_plural': 'Shartnomalar',
                'ordering': ['-created_at'],
            },
        ),
    ]