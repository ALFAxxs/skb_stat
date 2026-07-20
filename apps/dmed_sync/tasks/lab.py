"""
DMED — Tahlil natijalari sinxronlash.
TODO: selector'larni to'ldiring.
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')


async def sync_lab_result(page: Page, result) -> str:
    """result — LabResult (laboratory app) yoki LabTestResultLog (patients app)"""
    from django.conf import settings
    from ..models import DMEDSyncRecord
    DMED_URL = getattr(settings, 'DMED_URL', '')

    patient_id = getattr(result, 'patient_card_id', None)
    pr = DMEDSyncRecord.objects.filter(
        entity_type=DMEDSyncRecord.ENTITY_PATIENT,
        entity_id=patient_id,
        status=DMEDSyncRecord.STATUS_DONE,
    ).first()
    if not pr or not pr.dmed_id:
        raise ValueError(f"Bemor #{patient_id} DMED'ga yuborilmagan")

    await page.goto(
        f"{DMED_URL}/patients/{pr.dmed_id}/lab/new",  # TODO: URL
        wait_until='networkidle',
    )

    # Tahlil nomi / kodi
    # TODO: LabResult'da template.name, LabTestResultLog'da test_name
    name = (
        getattr(result, 'template', None) and result.template.name
        or getattr(result, 'test_name', '')
    )
    await page.fill('TODO_LAB_NAME_SELECTOR', name)

    # Natija qiymatlari
    # LabResult uchun result.values.all() → har bir qiymat
    # await page.fill('TODO_LAB_RESULT_SELECTOR', ...)

    await page.click('TODO_SAVE_BUTTON_SELECTOR')
    await page.wait_for_load_state('networkidle')

    dmed_id = ''  # TODO
    logger.info(f"Lab natija #{result.pk} DMED ga yuborildi.")
    return dmed_id
