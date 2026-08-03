from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dmed_sync', '0002_session_storage_state'),
    ]

    operations = [
        migrations.CreateModel(
            name='DMEDLoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('started',     'Boshlandi'),
                        ('opening',     'Brauzer ochilmoqda'),
                        ('waiting_otp', 'SMS kod kutilmoqda'),
                        ('submitting',  'Kod tasdiqlanmoqda'),
                        ('done',        'Muvaffaqiyatli'),
                        ('failed',      'Xato'),
                    ],
                    db_index=True, default='started', max_length=20,
                )),
                ('otp_code',   models.CharField(blank=True, max_length=10)),
                ('error',      models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'DMED Login urinishi', 'ordering': ['-created_at']},
        ),
    ]
