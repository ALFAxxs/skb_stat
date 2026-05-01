from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='is_operation',
            field=models.BooleanField(
                default=False,
                verbose_name='Operatsiyami?'
            ),
        ),
    ]
