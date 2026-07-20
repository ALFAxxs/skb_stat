"""
Django signals — model o'zgarganda DMEDSyncRecord navbatga qo'shadi.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import DMEDSyncRecord


# ─── Bemor kartasi ────────────────────────────────────────────────────────────
def _enqueue_patient(patient):
    DMEDSyncRecord.enqueue(
        entity_type=DMEDSyncRecord.ENTITY_PATIENT,
        entity_id=patient.pk,
        entity_repr=patient.full_name,
    )
    # Visit ma'lumotlari ham bitta kartada — alohida navbatga
    DMEDSyncRecord.enqueue(
        entity_type=DMEDSyncRecord.ENTITY_VISIT,
        entity_id=patient.pk,
        entity_repr=f"{patient.full_name} — qabul",
    )


# ─── PatientService (billing app yoki patients) ───────────────────────────────
def _enqueue_service(ps):
    patient_name = ''
    try:
        patient_name = ps.patient_card.full_name
    except Exception:
        pass
    DMEDSyncRecord.enqueue(
        entity_type=DMEDSyncRecord.ENTITY_SERVICE,
        entity_id=ps.pk,
        entity_repr=f"{patient_name} — {getattr(ps, 'service', None) and ps.service.name or ''}",
    )


# ─── LabResult (laboratory app) ───────────────────────────────────────────────
def _enqueue_lab(result):
    patient_name = ''
    try:
        patient_name = result.patient_card.full_name
    except Exception:
        pass
    name = getattr(result, 'template', None) and result.template.name or ''
    DMEDSyncRecord.enqueue(
        entity_type=DMEDSyncRecord.ENTITY_LAB,
        entity_id=result.pk,
        entity_repr=f"{patient_name} — {name}",
    )


# ─── LabTestResultLog (patients app — matnli natija) ─────────────────────────
def _enqueue_lab_text(log):
    patient_name = ''
    try:
        patient_name = log.assignment.patient_card.full_name
    except Exception:
        pass
    DMEDSyncRecord.enqueue(
        entity_type=DMEDSyncRecord.ENTITY_LAB,
        entity_id=log.pk,
        entity_repr=f"{patient_name} — {log.assignment.test_name if hasattr(log, 'assignment') else ''}",
    )


def connect_signals():
    """apps.py → ready() dan chaqiriladi."""

    # PatientCard
    from apps.patients.models import PatientCard
    post_save.connect(
        lambda sender, instance, **kw: _enqueue_patient(instance),
        sender=PatientCard,
        weak=False,
        dispatch_uid='dmed_patient_sync',
    )

    # LabTestResultLog
    from apps.patients.models import LabTestResultLog
    post_save.connect(
        lambda sender, instance, **kw: _enqueue_lab_text(instance),
        sender=LabTestResultLog,
        weak=False,
        dispatch_uid='dmed_lab_text_sync',
    )

    # DiagnosticResultLog
    try:
        from apps.patients.models import DiagnosticResultLog
        post_save.connect(
            lambda sender, instance, **kw: DMEDSyncRecord.enqueue(
                DMEDSyncRecord.ENTITY_DIAGNOSTIC, instance.pk,
                str(instance),
            ),
            sender=DiagnosticResultLog,
            weak=False,
            dispatch_uid='dmed_diagnostic_sync',
        )
    except ImportError:
        pass

    # LabResult (laboratory app — parametrik)
    try:
        from apps.laboratory.models import LabResult
        post_save.connect(
            lambda sender, instance, **kw: _enqueue_lab(instance),
            sender=LabResult,
            weak=False,
            dispatch_uid='dmed_labresult_sync',
        )
    except ImportError:
        pass

    # PatientService (billing)
    try:
        from apps.billing.models import PatientService
        post_save.connect(
            lambda sender, instance, **kw: _enqueue_service(instance),
            sender=PatientService,
            weak=False,
            dispatch_uid='dmed_service_sync',
        )
    except ImportError:
        pass
