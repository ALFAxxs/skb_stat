from django.db import migrations


def _copy_fk(model, old_field, new_field, mapping):
    old_col = f'{old_field}_id'
    new_col = f'{new_field}_id'
    for row in model.objects.exclude(**{f'{old_col}__isnull': True}):
        new_id = mapping.get(getattr(row, old_col))
        if new_id:
            setattr(row, new_col, new_id)
            row.save(update_fields=[new_field])


def backfill(apps, schema_editor):
    Doctor = apps.get_model('patients', 'Doctor')
    PatientTransfer = apps.get_model('patients', 'PatientTransfer')

    mapping = {d.pk: d.user_id for d in Doctor.objects.all() if d.user_id}

    _copy_fk(PatientTransfer, 'from_doctor', 'from_doctor_v2', mapping)
    _copy_fk(PatientTransfer, 'from_dept_head', 'from_dept_head_v2', mapping)
    _copy_fk(PatientTransfer, 'to_doctor', 'to_doctor_v2', mapping)
    _copy_fk(PatientTransfer, 'to_dept_head', 'to_dept_head_v2', mapping)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0048_patienttransfer_doctor_v2'),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
