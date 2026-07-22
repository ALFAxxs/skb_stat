"""
Entity turidan kelib chiqib to'g'ri sync funksiyasini chaqiradi.
"""
import asyncio
import logging
import traceback

from asgiref.sync import sync_to_async

from ..models import DMEDSyncRecord
from ..browser import dmed_session

logger = logging.getLogger('dmed_sync')

MAX_ATTEMPTS = 3


def _role_for(entity_type: str) -> str:
    """Entity turidan DMED rol nomini qaytaradi."""
    from django.conf import settings
    role_map = getattr(settings, 'DMED_ROLE_MAP', {})
    return role_map.get(entity_type, '')


async def _run_one(record: DMEDSyncRecord):
    """Bitta DMEDSyncRecord ni sinxronlaydi."""
    if record.attempts >= MAX_ATTEMPTS:
        await sync_to_async(record.mark_failed)(
            f'Maksimal urinishlar soni ({MAX_ATTEMPTS}) oshib ketdi'
        )
        return

    await sync_to_async(record.mark_running)()
    role = _role_for(record.entity_type)

    try:
        async with dmed_session(role=role) as page:
            dmed_id = ''

            if record.entity_type == DMEDSyncRecord.ENTITY_PATIENT:
                from apps.patients.models import PatientCard
                from .patient import sync_patient
                obj = await sync_to_async(PatientCard.objects.get)(pk=record.entity_id)
                dmed_id = await sync_patient(page, obj)

            elif record.entity_type == DMEDSyncRecord.ENTITY_VISIT:
                from apps.patients.models import PatientCard
                from .visit import sync_visit
                # attending_doctor va xizmatlarni oldindan yuklash
                obj = await sync_to_async(
                    lambda: PatientCard.objects
                    .select_related('attending_doctor')
                    .prefetch_related('patientservice_set__service')
                    .get(pk=record.entity_id)
                )()
                dmed_id = await sync_visit(page, obj)

            elif record.entity_type == DMEDSyncRecord.ENTITY_SERVICE:
                from .services import sync_patient_service
                try:
                    from apps.billing.models import PatientService
                except ImportError:
                    from apps.patients.models import PatientService
                obj = await sync_to_async(
                    PatientService.objects.select_related('service', 'patient_card').get
                )(pk=record.entity_id)
                dmed_id = await sync_patient_service(page, obj)

            elif record.entity_type == DMEDSyncRecord.ENTITY_LAB:
                from .lab import sync_lab_result
                try:
                    from apps.laboratory.models import LabResult
                    obj = await sync_to_async(LabResult.objects.get)(pk=record.entity_id)
                except Exception:
                    from apps.patients.models import LabTestResultLog
                    obj = await sync_to_async(LabTestResultLog.objects.get)(pk=record.entity_id)
                dmed_id = await sync_lab_result(page, obj)

            else:
                await sync_to_async(record.mark_failed)(
                    f"Noma'lum entity turi: {record.entity_type}"
                )
                return

            await sync_to_async(record.mark_done)(dmed_id=dmed_id)

    except Exception as exc:
        err = traceback.format_exc()
        logger.error(f"DMED sync xato [{record}]: {err}")
        await sync_to_async(record.mark_failed)(str(exc)[:500])


def run_pending():
    """Pending yozuvlarni ishlatish — worker thread'dan chaqiriladi."""
    qs = list(
        DMEDSyncRecord.objects.filter(
            status__in=[DMEDSyncRecord.STATUS_PENDING, DMEDSyncRecord.STATUS_FAILED]
        ).exclude(attempts__gte=MAX_ATTEMPTS).order_by('enqueued_at')[:50]
    )
    if not qs:
        return

    async def _batch():
        for record in qs:
            await _run_one(record)

    asyncio.run(_batch())
