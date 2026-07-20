"""
DMED — Statsionar / Ambulator qabulni sinxronlash.

TODO: selector'larni DMED'ga mos ravishda to'ldiring.
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')


async def sync_visit(page: Page, patient) -> str:
    """
    PatientCard (visit ma'lumotlari — qabul sanasi, shifokor, bo'lim) ni DMED'ga yuboradi.
    """
    from django.conf import settings
    DMED_URL = getattr(settings, 'DMED_URL', '')

    # ── 1. Qabul qo'shish sahifasini ochish ──────────────────────────────
    # Avval DMED'dagi bemor ID kerak — uni DMEDSyncRecord'dan olamiz
    from ..models import DMEDSyncRecord
    pr = DMEDSyncRecord.objects.filter(
        entity_type=DMEDSyncRecord.ENTITY_PATIENT,
        entity_id=patient.pk,
        status=DMEDSyncRecord.STATUS_DONE,
    ).first()

    dmed_patient_id = pr.dmed_id if pr else ''
    if not dmed_patient_id:
        raise ValueError(f"Bemor #{patient.pk} avval DMED'ga yuborilmagan — visit yuborib bo'lmaydi")

    # TODO: DMED'da qabul qo'shish URL'i
    await page.goto(f"{DMED_URL}/patients/{dmed_patient_id}/visits/new", wait_until='networkidle')

    # ── 2. Maydonlarni to'ldirish ─────────────────────────────────────────
    visit_type = patient.visit_type  # 'inpatient' yoki 'ambulatory'

    # Qabul sanasi
    admit_date = patient.admission_date.strftime('%d.%m.%Y') if patient.admission_date else ''
    await page.fill('TODO_ADMIT_DATE_SELECTOR', admit_date)

    # Qabul turi (statsionar/ambulator)
    # TODO: radio yoki select
    # await page.click(f'TODO_VISIT_TYPE_{visit_type.upper()}_SELECTOR')

    # Bo'lim
    # await page.select_option('TODO_DEPARTMENT_SELECTOR', patient.department.name if patient.department else '')

    # Shifokor
    # await page.select_option('TODO_DOCTOR_SELECTOR', ...)

    # ── 3. Saqlash ────────────────────────────────────────────────────────
    await page.click('TODO_SAVE_BUTTON_SELECTOR')
    await page.wait_for_load_state('networkidle')

    dmed_id = ''  # TODO
    logger.info(f"Qabul (bemor #{patient.pk}) DMED ga yuborildi.")
    return dmed_id
