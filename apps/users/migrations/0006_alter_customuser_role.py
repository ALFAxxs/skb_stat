from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_alter_customuser_groups_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(
                choices=[
                    ('admin', 'Administrator'),
                    ('doctor', 'Shifokor'),
                    ('statistician', 'Statistik'),
                    ('reception', 'Qabulxona'),
                    ('laborant', 'Laborant'),
                    ('viewer', "Faqat ko'rish"),
                ],
                default='viewer',
                max_length=20,
            ),
        ),
    ]
