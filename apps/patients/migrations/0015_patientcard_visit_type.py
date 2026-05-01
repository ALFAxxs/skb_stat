

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0014_departmenttransfer'),
    ]

    operations = [
        migrations.AddField(
            model_name='patientcard',
            name='visit_type',
            field=models.CharField(
                choices=[("inpatient", "Statsionar (yotqizilgan)"), ("ambulatory", "Ambulator (kunlik)")],
                default="inpatient",
                max_length=15,
                verbose_name="Tashrif turi",
            ),
        ),
    ]
