from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0046_doctor_to_user_backfill'),
    ]

    operations = [
        migrations.RemoveField(model_name='patientcard', name='attending_doctor'),
        migrations.RenameField(model_name='patientcard', old_name='attending_doctor_v2', new_name='attending_doctor'),
        migrations.RemoveField(model_name='patientcard', name='department_head'),
        migrations.RenameField(model_name='patientcard', old_name='department_head_v2', new_name='department_head'),
        migrations.RemoveField(model_name='ambulatoryconsultation', name='doctor'),
        migrations.RenameField(model_name='ambulatoryconsultation', old_name='doctor_v2', new_name='doctor'),
        migrations.RemoveField(model_name='doctortexttemplate', name='doctor'),
        migrations.RenameField(model_name='doctortexttemplate', old_name='doctor_v2', new_name='doctor'),
        migrations.RemoveField(model_name='treatmentprocedure', name='assigned_by'),
        migrations.RenameField(model_name='treatmentprocedure', old_name='assigned_by_v2', new_name='assigned_by'),
        migrations.RemoveField(model_name='prescription', name='doctor'),
        migrations.RenameField(model_name='prescription', old_name='doctor_v2', new_name='doctor'),
        migrations.RemoveField(model_name='labtestassignment', name='assigned_by'),
        migrations.RenameField(model_name='labtestassignment', old_name='assigned_by_v2', new_name='assigned_by'),
        migrations.RemoveField(model_name='diagnosticassignment', name='assigned_by'),
        migrations.RenameField(model_name='diagnosticassignment', old_name='assigned_by_v2', new_name='assigned_by'),
        migrations.RemoveField(model_name='consultationrequest', name='requested_by'),
        migrations.RenameField(model_name='consultationrequest', old_name='requested_by_v2', new_name='requested_by'),
        migrations.RemoveField(model_name='consultationrequest', name='consultants'),
        migrations.RenameField(model_name='consultationrequest', old_name='consultants_v2', new_name='consultants'),
    ]
