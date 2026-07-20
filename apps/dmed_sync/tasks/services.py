"""
DMED — PatientService (bemor xizmatlari) sinxronlash.
TODO: selector'larni to'ldiring.
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')


async def sync_patient_service(page: Page, ps) -> str:
    """ps — PatientService ob'ekti"""
    from django.conf import settings
    from ..models import DMEDSyncRecord
    DMED_URL = getattr(settings, 'DMED_URL', '')

    # Bemor DMED ID
    pr = DMEDSyncRecord.objects.filter(
        entity_type=DMEDSyncRecord.ENTITY_PATIENT,
        entity_id=ps.patient_card_id,
        status=DMEDSyncRecord.STATUS_DONE,
    ).first()
    if not pr or not pr.dmed_id:
        raise ValueError(f"Bemor #{ps.patient_card_id} DMED'ga yuborilmagan")

    await page.goto(
        f"{DMED_URL}/patients/{pr.dmed_id}/services/new",  # TODO: URL
        wait_until='networkidle',
    )

    # Xizmat nomi
    await page.fill('TODO_SERVICE_NAME_SELECTOR', ps.service.name)  # yoki kodi
    # await page.fill('TODO_SERVICE_CODE_SELECTOR', ps.service.code or '')

    # Narx
    # await page.fill('TODO_SERVICE_PRICE_SELECTOR', str(ps.price))

    # Sana
    svc_date = ps.ordered_at.strftime('%d.%m.%Y') if ps.ordered_at else ''
    # await page.fill('TODO_SERVICE_DATE_SELECTOR', svc_date)

    await page.click('TODO_SAVE_BUTTON_SELECTOR')
    await page.wait_for_load_state('networkidle')

    dmed_id = ''  # TODO
    logger.info(f"PatientService #{ps.pk} DMED ga yuborildi.")
    return dmed_id
