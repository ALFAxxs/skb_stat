from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('care', '0002_medicationorder_prescribed_by_v2_and_more'),
        ('patients', '0046_doctor_to_user_backfill'),
    ]

    operations = [
        migrations.RemoveField(model_name='medicationorder', name='prescribed_by'),
        migrations.RenameField(model_name='medicationorder', old_name='prescribed_by_v2', new_name='prescribed_by'),
        migrations.RemoveField(model_name='referral', name='referring_doctor'),
        migrations.RenameField(model_name='referral', old_name='referring_doctor_v2', new_name='referring_doctor'),
        migrations.RemoveField(model_name='referral', name='target_doctor'),
        migrations.RenameField(model_name='referral', old_name='target_doctor_v2', new_name='target_doctor'),
    ]
