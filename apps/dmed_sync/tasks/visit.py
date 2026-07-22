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
      'inpatient':  '2073',  # Kasalxona 🛏
      'ambulatory': '1859',  # Maslahatlar 🩺
  }
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')

# DMED radio value → xizmat kategoriyasi
DEFAULT_CATEGORY_MAP = {
    'inpatient':  '2073',  # Kasalxona 🛏
    'ambulatory': '1859',  # Maslahatlar 🩺
}


async def _select_price_category(page: Page):
    """Narxlar ro'yxati toifasi — birinchi mavjud variantni tanlaydi."""
    price_input = page.locator(
        '.create-appointment-secondary-form .el-select__input'
    ).first
    await price_input.wait_for(state='visible', timeout=10_000)
    await price_input.click()

    first_opt = page.locator(
        '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item'
    ).first
    await first_opt.wait_for(state='visible', timeout=10_000)
    await first_opt.click()


async def _select_service_radio(page: Page, radio_value: str):
    """Xizmat kategoriyasi radio tugmasini JS orqali bosadi (Element UI)."""
    await page.evaluate(
        f'document.querySelector(\'input.el-radio__original[value="{radio_value}"]\').click()'
    )
    # Xizmatlar ro'yxati yuklanishini kutish
    await page.wait_for_load_state('networkidle', timeout=10_000)


async def _select_doctor(page: Page, doctor_name: str):
    """Shifokorni izlash — ism bo'yicha qidiradi va birinchi natijani tanlaydi."""
    doctor_input = page.locator('.create-appointment__select-doctor .el-select__input')
    await doctor_input.wait_for(state='visible', timeout=10_000)
    await doctor_input.click()
    await doctor_input.type(doctor_name[:15], delay=60)  # 15 harf qidiruv uchun yetarli

    first_opt = page.locator(
        '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item'
    ).first
    await first_opt.wait_for(state='visible', timeout=10_000)
    await first_opt.click()


async def _select_services(page: Page, service_names: list[str]):
    """
    Xizmatlar checkboxlarini nomlar bo'yicha tanlaydi.
    Mos kelmaganlarni o'tkazib yuboradi.
    """
    if not service_names:
        return

    for name in service_names:
        # Xizmat nomi bo'yicha label topish (qisman moslik)
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
    if not jshshir or len(jshshir) != 14:
        raise ValueError(f"Bemor #{patient.pk} JSHSHIR yo'q: '{jshshir}'")

    # ── 1. Sahifani ochish ─────────────────────────────────────────────────
    await page.goto(
        f"{DMED_URL}/appointments/create",
        wait_until='networkidle',
        timeout=20_000,
    )

    # ── 2. JSHSHIR kiritish va qidirish ───────────────────────────────────
    jshshir_input = page.locator('input[data-maska="##############"]').first
    await jshshir_input.wait_for(state='visible', timeout=10_000)
    await jshshir_input.click()
    await page.keyboard.press('Control+a')
    await page.keyboard.type(jshshir)

    search_btn = page.locator(
        '.select-patient-form__search-btns .el-button--primary'
    ).first
    await search_btn.click()

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
        raise ValueError(f"Bemor #{patient.pk} DMED'da topilmadi (JSHSHIR: {jshshir})")

    # ── 3. Narx toifasini tanlash ─────────────────────────────────────────
    await _select_price_category(page)

    # ── 4. Xizmat kategoriyasi radio ──────────────────────────────────────
    visit_type = getattr(patient, 'visit_type', 'ambulatory')
    radio_value = category_map.get(visit_type, '1859')
    await _select_service_radio(page, radio_value)

    # ── 5. Shifokorni tanlash ─────────────────────────────────────────────
    doctor_name = ''
    if patient.attending_doctor:
        doc = patient.attending_doctor
        doctor_name = (
            doc.get_full_name()
            if hasattr(doc, 'get_full_name')
            else str(doc)
        )
    if doctor_name:
        await _select_doctor(page, doctor_name)
        # Doctor tanlanib xizmatlar yuklanishini kutish
        await page.wait_for_load_state('networkidle', timeout=8_000)

    # ── 6. Xizmatlar checkboxlari ─────────────────────────────────────────
    # __init__.py da prefetch_related qilingan, shuning uchun DB ga qayta murojaat yo'q
    service_names = []
    try:
        from asgiref.sync import sync_to_async
        ps_list = await sync_to_async(
            lambda: list(patient.patientservice_set.select_related('service').all())
        )()
        for ps in ps_list:
            if ps.service and ps.service.name:
                service_names.append(ps.service.name)
    except Exception:
        pass

    if service_names:
        await _select_services(page, service_names)

    # ── 7. Saqlash ────────────────────────────────────────────────────────
    # Saqlash tugmasini topish (oxirgi primary tugma, disabled emas)
    save_btn = page.locator(
        'button.el-button--primary:not(.is-plain):not(.is-disabled)'
    ).last
    await save_btn.wait_for(state='visible', timeout=8_000)
    await save_btn.click()
    await page.wait_for_load_state('networkidle', timeout=15_000)

    # ── 8. DMED dan qabul ID ni olish ─────────────────────────────────────
    dmed_id = ''
    if '/appointments/' in page.url:
        parts = page.url.rstrip('/').split('/')
        if parts[-1].isdigit():
            dmed_id = parts[-1]

    logger.info(
        f"Qabul (bemor #{patient.pk}, {patient.full_name}) DMED'ga yuborildi. "
        f"ID: {dmed_id or '?'} | URL: {page.url}"
    )
    return dmed_id
