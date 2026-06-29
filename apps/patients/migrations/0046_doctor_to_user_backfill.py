import re

from django.contrib.auth.hashers import make_password
from django.db import migrations


def _make_username(full_name, pk, exists_check, taken):
    base = re.sub(r'[^a-z0-9]+', '', (full_name or '').lower())[:20] or f'doctor{pk}'
    candidate = base
    i = 1
    while candidate in taken or exists_check(candidate):
        i += 1
        candidate = f"{base}{i}"
    taken.add(candidate)
    return candidate


def _copy_fk(model, old_field, new_field, mapping):
    old_col = f'{old_field}_id'
    new_col = f'{new_field}_id'
    for row in model.objects.exclude(**{f'{old_col}__isnull': True}):
        new_id = mapping.get(getattr(row, old_col))
        if new_id:
            setattr(row, new_col, new_id)
            row.save(update_fields=[new_field])


def link_and_backfill(apps, schema_editor):
    Doctor = apps.get_model('patients', 'Doctor')
    CustomUser = apps.get_model('users', 'CustomUser')
    PatientCard = apps.get_model('patients', 'PatientCard')
    AmbulatoryConsultation = apps.get_model('patients', 'AmbulatoryConsultation')
    DoctorTextTemplate = apps.get_model('patients', 'DoctorTextTemplate')
    TreatmentProcedure = apps.get_model('patients', 'TreatmentProcedure')
    Prescription = apps.get_model('patients', 'Prescription')
    LabTestAssignment = apps.get_model('patients', 'LabTestAssignment')
    DiagnosticAssignment = apps.get_model('patients', 'DiagnosticAssignment')
    ConsultationRequest = apps.get_model('patients', 'ConsultationRequest')
    Service = apps.get_model('services', 'Service')
    PatientService = apps.get_model('services', 'PatientService')
    PatientMedicine = apps.get_model('services', 'PatientMedicine')
    Referral = apps.get_model('care', 'Referral')
    MedicationOrder = apps.get_model('care', 'MedicationOrder')

    taken_usernames = set()
    mapping = {}  # Doctor.pk -> CustomUser.pk

    for doctor in Doctor.objects.all():
        user = doctor.user
        if user is None:
            username = _make_username(
                doctor.full_name, doctor.pk,
                lambda c: CustomUser.objects.filter(username=c).exists(),
                taken_usernames,
            )
            user = CustomUser.objects.create(
                username=username,
                first_name=doctor.full_name or username,
                role='doctor',
                department_id=doctor.department_id,
                is_head=doctor.is_head,
                is_general_practitioner=doctor.is_general_practitioner,
                is_active=doctor.is_active,
                password=make_password(None),
            )
            doctor.user = user
            doctor.save(update_fields=['user'])
        else:
            user.department_id = doctor.department_id
            user.is_head = doctor.is_head
            user.is_general_practitioner = doctor.is_general_practitioner
            user.save(update_fields=['department', 'is_head', 'is_general_practitioner'])
        mapping[doctor.pk] = user.pk

    _copy_fk(PatientCard, 'attending_doctor', 'attending_doctor_v2', mapping)
    _copy_fk(PatientCard, 'department_head', 'department_head_v2', mapping)
    _copy_fk(AmbulatoryConsultation, 'doctor', 'doctor_v2', mapping)
    _copy_fk(DoctorTextTemplate, 'doctor', 'doctor_v2', mapping)
    _copy_fk(TreatmentProcedure, 'assigned_by', 'assigned_by_v2', mapping)
    _copy_fk(Prescription, 'doctor', 'doctor_v2', mapping)
    _copy_fk(LabTestAssignment, 'assigned_by', 'assigned_by_v2', mapping)
    _copy_fk(DiagnosticAssignment, 'assigned_by', 'assigned_by_v2', mapping)
    _copy_fk(ConsultationRequest, 'requested_by', 'requested_by_v2', mapping)
    _copy_fk(PatientService, 'ordered_by', 'ordered_by_v2', mapping)
    _copy_fk(PatientService, 'performed_by', 'performed_by_v2', mapping)
    _copy_fk(PatientMedicine, 'ordered_by', 'ordered_by_v2', mapping)
    _copy_fk(Referral, 'referring_doctor', 'referring_doctor_v2', mapping)
    _copy_fk(Referral, 'target_doctor', 'target_doctor_v2', mapping)
    _copy_fk(MedicationOrder, 'prescribed_by', 'prescribed_by_v2', mapping)

    for cr in ConsultationRequest.objects.prefetch_related('consultants').all():
        ids = [mapping[d.pk] for d in cr.consultants.all() if d.pk in mapping]
        if ids:
            cr.consultants_v2.set(ids)

    for svc in Service.objects.prefetch_related('assigned_doctors').all():
        ids = [mapping[d.pk] for d in svc.assigned_doctors.all() if d.pk in mapping]
        if ids:
            svc.assigned_doctors_v2.set(ids)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0045_ambulatoryconsultation_doctor_v2_and_more'),
        ('services', '0011_patientmedicine_ordered_by_v2_and_more'),
        ('care', '0002_medicationorder_prescribed_by_v2_and_more'),
        ('users', '0012_add_doctor_flags'),
    ]

    operations = [
        migrations.RunPython(link_and_backfill, noop),
    ]
