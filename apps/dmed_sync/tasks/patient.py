"""
DMED — Bemor JSHSHIR orqali topish.
appointments/create sahifasida JSHSHIR kiritib qidiradi,
tibbiy karta raqamini (DMED ID) qaytaradi.
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')


async def sync_patient(page: Page, patient) -> str:
    """
    DMED'da bemor mavjudligini JSHSHIR orqali tekshiradi.
    Tibbiy karta raqamini qaytaradi (keyingi sync'lar uchun DMED ID).
    """
    from django.conf import settings
    DMED_URL = getattr(settings, 'DMED_URL', '') or 'https://mis.dmed.uz'

    jshshir = (patient.JSHSHIR or '').strip()
    if not jshshir or len(jshshir) != 14:
        raise ValueError(
            f"Bemor #{patient.pk} da to'g'ri JSHSHIR yo'q: '{jshshir}'"
        )

    # ── 1. Qabul yaratish sahifasini ochish ───────────────────────────────
    await page.goto(
        f"{DMED_URL}/appointments/create",
        wait_until='networkidle',
        timeout=20_000,
    )

    # "Hujjatlar bo'yicha qidirish" tab default active,
    # "Hujjat turi" = JSHSHIR default tanlangan
    jshshir_input = page.locator('input[data-maska="##############"]').first
    await jshshir_input.wait_for(state='visible', timeout=10_000)
    await jshshir_input.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type(jshshir)

    # ── 2. "Topish" tugmasi ───────────────────────────────────────────────
    search_btn = page.locator(
        '.select-patient-form__search-btns .el-button--primary'
    ).first
    await search_btn.click()

    # ── 3. Bemor ma'lumotlari chiqishini kutish ───────────────────────────
    # Tibbiy karta raqami linki 'disabled' holdan 'enabled' ga o'tadi
    try:
        await page.wait_for_function(
            """() => {
                const btn = document.querySelector(
                    '.selected-patient-info .el-button.is-link'
                );
                return btn && !btn.disabled && btn.textContent.trim() !== '-';
            }""",
            timeout=15_000,
        )
    except Exception:
        raise ValueError(
            f"Bemor #{patient.pk} DMED'da topilmadi (JSHSHIR: {jshshir})"
        )

    # ── 4. Tibbiy karta raqamini olish (DMED ID) ─────────────────────────
    card_btn = page.locator('.selected-patient-info .el-button.is-link')
    dmed_id = (await card_btn.inner_text()).strip()

    logger.info(
        f"Bemor #{patient.pk} ({patient.full_name}) DMED'da topildi. "
        f"Tibbiy karta: {dmed_id}"
    )
    return dmed_id
