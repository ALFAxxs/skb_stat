from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0049_patienttransfer_backfill'),
    ]

    operations = [
        migrations.RemoveField(model_name='patienttransfer', name='from_doctor'),
        migrations.RenameField(model_name='patienttransfer', old_name='from_doctor_v2', new_name='from_doctor'),
        migrations.RemoveField(model_name='patienttransfer', name='from_dept_head'),
        migrations.RenameField(model_name='patienttransfer', old_name='from_dept_head_v2', new_name='from_dept_head'),
        migrations.RemoveField(model_name='patienttransfer', name='to_doctor'),
        migrations.RenameField(model_name='patienttransfer', old_name='to_doctor_v2', new_name='to_doctor'),
        migrations.RemoveField(model_name='patienttransfer', name='to_dept_head'),
        migrations.RenameField(model_name='patienttransfer', old_name='to_dept_head_v2', new_name='to_dept_head'),
    ]
