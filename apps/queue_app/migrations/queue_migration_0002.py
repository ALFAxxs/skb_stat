from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('queue_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='QueueSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True)),
                ('audio_mode', models.CharField(
                    choices=[
                        ('beep',  '🔔 Signal (ding)'),
                        ('voice', '🔊 Ovozli chaqiruv'),
                        ('both',  '🔔🔊 Ikkalasi'),
                        ('off',   '🔇 Ovozsiz'),
                    ],
                    default='beep', max_length=10, verbose_name='Audio rejim'
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Navbat sozlamalari',
                'verbose_name_plural': 'Navbat sozlamalari',
            },
        ),
    ]