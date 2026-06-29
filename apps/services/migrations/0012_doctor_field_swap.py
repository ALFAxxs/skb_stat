from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0011_patientmedicine_ordered_by_v2_and_more'),
        ('patients', '0046_doctor_to_user_backfill'),
    ]

    operations = [
        migrations.RemoveField(model_name='service', name='assigned_doctors'),
        migrations.RenameField(model_name='service', old_name='assigned_doctors_v2', new_name='assigned_doctors'),
        migrations.RemoveField(model_name='patientservice', name='ordered_by'),
        migrations.RenameField(model_name='patientservice', old_name='ordered_by_v2', new_name='ordered_by'),
        migrations.RemoveField(model_name='patientservice', name='performed_by'),
        migrations.RenameField(model_name='patientservice', old_name='performed_by_v2', new_name='performed_by'),
        migrations.RemoveField(model_name='patientmedicine', name='ordered_by'),
        migrations.RenameField(model_name='patientmedicine', old_name='ordered_by_v2', new_name='ordered_by'),
    ]
