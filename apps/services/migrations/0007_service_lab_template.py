# Generated migration: add lab_template FK to Service

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('laboratory', '0001_initial'),
        ('services', '0006_servicepackage_servicepackageitem_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='lab_template',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='linked_services',
                to='laboratory.labtemplate',
                verbose_name='Lab shabloni'
            ),
        ),
    ]
