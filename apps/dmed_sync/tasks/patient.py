"""
DMED — Bemor JSHSHIR orqali topish.
appointments/create sahifasida JSHSHIR kiritib qidiradi,
tibbiy karta raqamini (DMED ID) qaytaradi.
"""
import logging
from playwright.async_api import Page

from ._dmed_helpers import fill_jshshir_and_search

logger = logging.getLogger('dmed_sync')


async def sync_patient(page: Page, patient) -> str:
    """
    DMED'da bemor mavjudligini JSHSHIR orqali tekshiradi.
    Tibbiy karta raqamini qaytaradi (keyingi sync'lar uchun DMED ID).
    """
    from django.conf import settings
    DMED_URL = getattr(settings, 'DMED_URL', '') or 'https://mis.dmed.uz'

    jshshir = (patient.JSHSHIR or '').strip()
    if not jshshir or len(jshshir) != 14 or not jshshir.isdigit():
        raise ValueError(
            f"Bemor #{patient.pk} da to'g'ri JSHSHIR yo'q: '{jshshir}'"
        )

    # ── 1. Sahifani ochish ─────────────────────────────────────────────────
    await page.goto(
        f"{DMED_URL}/appointments/create",
        wait_until='domcontentloaded',
        timeout=30_000,
    )
    await page.wait_for_timeout(800)

    # Redirect tekshiruvi (session tugagan bo'lishi mumkin)
    if '/auth/' in page.url:
        raise RuntimeError(
            f"Bemor #{patient.pk}: /appointments/create ga o'tishda redirect "
            f"({page.url}). Session muddati tugagan."
        )

    # ── 2. JSHSHIR kiritish, qidirish, natijani kutish ────────────────────
    await fill_jshshir_and_search(page, jshshir, patient.pk)

    # ── 3. Tibbiy karta raqamini olish (DMED ID) ─────────────────────────
    card_btn = page.locator('.selected-patient-info .el-button.is-link')
    dmed_id = (await card_btn.inner_text()).strip()

    logger.info(
        f"Bemor #{patient.pk} ({patient.full_name}) DMED'da topildi. "
        f"Tibbiy karta: {dmed_id}"
    )
    return dmed_id
