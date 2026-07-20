"""
DMED — Bemor kartasini sinxronlash.

TODO: Har bir `page.fill(...)` va `page.click(...)` qatoridagi selector'ni
      DMED'ning haqiqiy HTML'iga qarab to'ldiring.
      Buning uchun: DMED'ni brauzerda oching → F12 → Elements →
      kerakli input'ni toping → id yoki name atributini nusxa oling.
"""
import logging
from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')


async def sync_patient(page: Page, patient) -> str:
    """
    PatientCard ob'ektini DMED'ga yuboradi.
    Qaytaradi: DMED tomonidan berilgan ID (str) yoki ''.
    """
    from django.conf import settings
    DMED_URL = getattr(settings, 'DMED_URL', '')

    # ── 1. DMED'da bemor bor-yo'qligini JSHSHIR orqali tekshirish ──────────
    # TODO: DMED qidiruv sahifasining URL va selectorlarini yozing
    # await page.goto(f"{DMED_URL}/patients/search?inn={patient.JSHSHIR}")
    # existing_row = await page.query_selector('TODO: jadval qatori selector')
    # if existing_row:
    #     dmed_id = await existing_row.get_attribute('data-id')  # TODO
    #     logger.info(f"Bemor #{patient.pk} allaqachon DMED da: {dmed_id}")
    #     return dmed_id

    # ── 2. Yangi bemor qo'shish sahifasini ochish ──────────────────────────
    await page.goto(f"{DMED_URL}/patients/new", wait_until='networkidle')  # TODO: URL

    # ── 3. Maydonlarni to'ldirish ─────────────────────────────────────────
    # TODO: quyidagi selector'larni DMED'ga mos ravishda o'zgartiring

    # F.I.SH
    await page.fill('TODO_FULLNAME_SELECTOR', patient.full_name)

    # Tug'ilgan sana (format DMED talab qilganidek: 'DD.MM.YYYY' yoki 'YYYY-MM-DD')
    birth = patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else ''
    await page.fill('TODO_BIRTHDATE_SELECTOR', birth)

    # Jinsi
    # TODO: DMED radio/select selector
    # gender_val = 'male' if patient.gender == 'M' else 'female'
    # await page.select_option('TODO_GENDER_SELECTOR', gender_val)

    # JSHSHIR
    if patient.JSHSHIR:
        await page.fill('TODO_JSHSHIR_SELECTOR', patient.JSHSHIR)

    # Pasport seriya
    if patient.passport_serial:
        await page.fill('TODO_PASSPORT_SELECTOR', patient.passport_serial)

    # Telefon
    if patient.phone:
        await page.fill('TODO_PHONE_SELECTOR', patient.phone)

    # Manzil / viloyat / tuman
    # TODO: dropdown'lar bo'lsa select_option ishlatiladi
    # await page.select_option('TODO_REGION_SELECTOR', patient.region.name if patient.region else '')

    # ── 4. Saqlash ────────────────────────────────────────────────────────
    await page.click('TODO_SAVE_BUTTON_SELECTOR')
    await page.wait_for_load_state('networkidle')

    # ── 5. DMED dan qaytgan ID ni olish ───────────────────────────────────
    # TODO: muvaffaqiyatli saqlanganda DMED URL'ga ID qo'shishi mumkin
    # Masalan: /patients/12345 → '12345'
    # dmed_id = page.url.split('/')[-1]

    dmed_id = ''  # TODO: haqiqiy ID ni oling
    logger.info(f"Bemor #{patient.pk} DMED ga yuborildi. DMED ID: {dmed_id or '?'}")
    return dmed_id
