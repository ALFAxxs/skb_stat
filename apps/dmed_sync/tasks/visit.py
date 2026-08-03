"""
DMED — Ambulator qabul yaratish (appointments/create).

Oqim:
  1. JSHSHIR orqali bemor topish
  2. Narx toifasi (birinchi mavjud)
  3. Xizmat kategoriyasi radio (visit_type / DMED_SERVICE_CATEGORY_MAP)
  4. Shifokor qidirish va tanlash
  5. Xizmatlar checkboxlari (PatientService nomlari bo'yicha moslashtirish)
  6. Saqlash

Settings (conf/settings.py):
  DMED_SERVICE_CATEGORY_MAP = {
      'inpatient':  '2073',  # Kasalxona
      'ambulatory': '1859',  # Maslahatlar
  }
"""
import logging
from asgiref.sync import sync_to_async
from playwright.async_api import Page

from ._dmed_helpers import fill_jshshir_and_search

logger = logging.getLogger('dmed_sync')

DEFAULT_CATEGORY_MAP = {
    'inpatient':  '2073',
    'ambulatory': '1859',
}


async def _wait_for_page_ready(page: Page, timeout: int = 10_000):
    """Sahifa networkidle ga o'rniga aktiv so'rovlar tugashini kutadi."""
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=timeout)
    except Exception:
        pass
    await page.wait_for_timeout(800)


async def _select_price_category(page: Page):
    """Narxlar ro'yxati toifasi — birinchi mavjud variantni tanlaydi."""
    price_input = page.locator(
        '.create-appointment-secondary-form .el-select__input'
    ).first
    await price_input.wait_for(state='visible', timeout=10_000)
    await price_input.click()
    await page.wait_for_timeout(500)

    first_opt = page.locator(
        '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item'
    ).first
    await first_opt.wait_for(state='visible', timeout=8_000)
    await first_opt.click()
    await page.wait_for_timeout(300)


async def _select_service_radio(page: Page, radio_value: str):
    """Xizmat kategoriyasi radio tugmasini JS orqali bosadi (Element UI)."""
    try:
        await page.evaluate(
            f'document.querySelector(\'input.el-radio__original[value="{radio_value}"]\').click()'
        )
    except Exception as exc:
        logger.warning(f'Radio value {radio_value} topilmadi: {exc}')
    await page.wait_for_timeout(1500)


async def _select_doctor(page: Page, doctor_name: str):
    """Shifokorni izlash — ism bo'yicha qidiradi va birinchi natijani tanlaydi."""
    try:
        doctor_input = page.locator('.create-appointment__select-doctor .el-select__input')
        await doctor_input.wait_for(state='visible', timeout=8_000)
        await doctor_input.click()
        await doctor_input.type(doctor_name[:15], delay=60)
        await page.wait_for_timeout(1000)

        first_opt = page.locator(
            '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item'
        ).first
        await first_opt.wait_for(state='visible', timeout=6_000)
        await first_opt.click()
        await page.wait_for_timeout(500)
    except Exception as exc:
        logger.warning(f"Shifokor '{doctor_name}' DMED da topilmadi: {exc}")


async def _select_services(page: Page, service_names: list[str]):
    """Xizmatlar checkboxlarini nomlar bo'yicha tanlaydi."""
    if not service_names:
        return

    for name in service_names:
        checkbox_label = page.locator(
            f'.appointment-service-list .el-checkbox__label:has-text("{name[:20]}")'
        ).first
        try:
            await checkbox_label.wait_for(state='visible', timeout=3_000)
            await checkbox_label.click()
            logger.info(f'Xizmat tanlandi: {name}')
        except Exception:
            logger.warning(f'Xizmat topilmadi (DMED da): {name}')


async def sync_visit(page: Page, patient) -> str:
    """
    PatientCard uchun DMED'da ambulator qabul yaratadi.
    Qaytaradi: DMED qabul ID (str) yoki ''.
    """
    from django.conf import settings
    DMED_URL = getattr(settings, 'DMED_URL', '') or 'https://mis.dmed.uz'
    category_map = getattr(settings, 'DMED_SERVICE_CATEGORY_MAP', DEFAULT_CATEGORY_MAP)

    jshshir = (patient.JSHSHIR or '').strip()
    if not jshshir or len(jshshir) != 14 or not jshshir.isdigit():
        raise ValueError(f"Bemor #{patient.pk} JSHSHIR yo'q: '{jshshir}'")

    # ── 1. Sahifani ochish ─────────────────────────────────────────────────
    await page.goto(
        f"{DMED_URL}/appointments/create",
        wait_until='domcontentloaded',
        timeout=30_000,
    )
    await page.wait_for_timeout(800)

    # Redirect tekshiruvi
    if '/auth/' in page.url:
        raise RuntimeError(
            f"Bemor #{patient.pk}: /appointments/create ga o'tishda redirect "
            f"({page.url}). Session muddati tugagan."
        )

    # ── 2. JSHSHIR kiritish, qidirish, natijani kutish ────────────────────
    await fill_jshshir_and_search(page, jshshir, patient.pk)

    # ── 3. Narx toifasini tanlash ─────────────────────────────────────────
    await _select_price_category(page)

    # ── 4. Xizmat kategoriyasi radio ──────────────────────────────────────
    visit_type = getattr(patient, 'visit_type', 'ambulatory') or 'ambulatory'
    radio_value = category_map.get(visit_type, '1859')
    await _select_service_radio(page, radio_value)

    # ── 5. Shifokorni tanlash ─────────────────────────────────────────────
    doctor_name = ''
    if patient.attending_doctor:
        doc = patient.attending_doctor
        doctor_name = (
            doc.get_full_name().strip()
            if hasattr(doc, 'get_full_name')
            else str(doc)
        )
    if doctor_name:
        await _select_doctor(page, doctor_name)
        await page.wait_for_timeout(1000)

    # ── 6. Xizmatlar — prefetch cache dan (qo'shimcha DB so'rovi yo'q) ────
    service_names = await sync_to_async(
        lambda: [
            ps.service.name
            for ps in patient.patient_services.all()
            if ps.service and ps.service.name
        ]
    )()
    if service_names:
        await _select_services(page, service_names)

    # ── 7. Saqlash ────────────────────────────────────────────────────────
    save_btn = page.locator(
        'button.el-button--primary:not(.is-plain):not(.is-disabled)'
    ).last
    await save_btn.wait_for(state='visible', timeout=8_000)
    await save_btn.click()
    await _wait_for_page_ready(page, timeout=15_000)

    # ── 8. DMED dan qabul ID ni olish ─────────────────────────────────────
    dmed_id = ''
    if '/appointments/' in page.url:
        parts = page.url.rstrip('/').split('/')
        if parts[-1].isdigit():
            dmed_id = parts[-1]

    logger.info(
        f"Qabul (bemor #{patient.pk}, {patient.full_name}, {visit_type}) DMED'ga yuborildi. "
        f"ID: {dmed_id or '?'} | URL: {page.url}"
    )
    return dmed_id
