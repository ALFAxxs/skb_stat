"""
DMED ga qo'lda login qilish buyrug'i.

Ishlatish:
    python manage.py dmed_login

Jarayon:
  1. Ko'rinadigan Chromium brauzer ochiladi
  2. PINFL avtomatik kiritiladi va yuboriladi
  3. Telefonga SMS keladi — terminalda 5 ta raqamni kiritasiz
  4. SMS kod brauzerga avtomatik kiritiladi
  5. Login bo'lgach session DB ga saqlanadi

Server (Linux) da ekran bo'lmasa:
    DISPLAY=:99 python manage.py dmed_login
    (avval `Xvfb :99 -screen 0 1280x900x24 &` ishga tushiring)
"""
import asyncio
import sys

from django.core.management.base import BaseCommand
from playwright.async_api import async_playwright

# ─── URL ─────────────────────────────────────────────────────────────────────
LOGIN_PAGE_URL = 'https://mis.dmed.uz/auth/login'

# ─── Tab bosqichi ─────────────────────────────────────────────────────────────
# Login sahifasida tablar bor: "DMED Pro ilovasi" tabiga bosish kerak
APP_TAB_SELECTOR = '#tab-app'

# ─── PINFL bosqichi ───────────────────────────────────────────────────────────
# data-maska barqaror, id dinamik o'zgaradi — uni ISHLATMAYMIZ
PINFL_SELECTOR = 'input[data-maska="##############"]'

# "Kodni olish" tugmasi — login__actions-submit barqaror klass
PINFL_SUBMIT_SELECTOR = 'button.login__actions-submit'

# ─── SMS (OTP) bosqichi ───────────────────────────────────────────────────────
# 5 ta alohida input, har biri bitta raqam
OTP_SELECTORS = [
    'input.login-page__otp-input.one',
    'input.login-page__otp-input.two',
    'input.login-page__otp-input.three',
    'input.login-page__otp-input.four',
    'input.login-page__otp-input.five',
]

# SMS kodni tasdiqlash tugmasi — TODO: OTP sahifasidagi tugma HTML'ini yuboring
OTP_SUBMIT_SELECTOR = 'button.login__actions-submit'

# ─── Login muvaffaqiyati tekshiruvi ──────────────────────────────────────────
# Login bo'lgach URL qanday ko'rinadi?
LOGIN_SUCCESS_URL_PART = '/auth/login'   # Agar bu URL DA BO'LMASA — login bo'lgan


class Command(BaseCommand):
    help = 'DMED ga PINFL + SMS orqali login qilib, session saqlaydi'

    def add_arguments(self, parser):
        parser.add_argument('--pinfl', type=str, default='',
                            help='PINFL (bo\'sh qolsa terminal so\'raydi)')
        parser.add_argument('--by', type=str, default='admin',
                            help='Kim login qilayotgani (log uchun)')

    def handle(self, *args, **options):
        pinfl   = options['pinfl'] or input('DMED PINFL kiriting: ').strip()
        by_user = options['by']

        if not pinfl or len(pinfl) != 14 or not pinfl.isdigit():
            self.stderr.write(self.style.ERROR('❌ PINFL 14 ta raqamdan iborat bo\'lishi kerak.'))
            return

        self.stdout.write(self.style.WARNING(
            '\n📌 Chromium brauzer ochilmoqda...\n'
            '   PINFL avtomatik kiritiladi.\n'
            '   SMS kelgach bu terminalda 5 ta raqamni kiriting.\n'
        ))

        asyncio.run(self._run(pinfl, by_user))

    async def _run(self, pinfl: str, by_user: str):
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(
                headless=False,
                slow_mo=250,
                args=['--start-maximized'],
            )
            context = await browser.new_context(
                viewport=None,
                locale='ru-RU',
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
            )
            page = await context.new_page()

            # ── 1-bosqich: Login sahifasini ochish ───────────────────────
            self.stdout.write(f'  → {LOGIN_PAGE_URL}')
            await page.goto(LOGIN_PAGE_URL, wait_until='networkidle', timeout=30_000)

            # ── 1b-bosqich: "DMED Pro ilovasi" tabiga bosish ─────────────
            try:
                await page.wait_for_selector(APP_TAB_SELECTOR, timeout=8_000)
                await page.click(APP_TAB_SELECTOR)
                self.stdout.write('  → "DMED Pro ilovasi" tabi tanlandi')
                await page.wait_for_timeout(500)
            except Exception as exc:
                self.stdout.write(f'  ⚠️  Tab topilmadi ({exc}), davom etamiz...')

            # ── 2-bosqich: PINFL kiritish ─────────────────────────────────
            try:
                await page.wait_for_selector(PINFL_SELECTOR, timeout=10_000)
                # vue-maska input: avval fill, keyin type (ikkinchisi trigger qiladi)
                await page.click(PINFL_SELECTOR)
                await page.keyboard.press('Control+a')
                await page.keyboard.type(pinfl, delay=80)
                self.stdout.write(f'  → PINFL kiritildi: {pinfl[:4]}**********')

                # 2 ta login__actions-submit bor — birinchisi (Kodni olish) JS orqali bosamiz
                await page.wait_for_timeout(500)
                await page.evaluate(
                    "document.querySelectorAll('button.login__actions-submit')[0].click()"
                )
                self.stdout.write('  → "Kodni olish" bosildi, SMS kutilmoqda...')

            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(
                        f'\n❌ PINFL kiritib bo\'lmadi: {exc}\n'
                        f'   Selector: {PINFL_SELECTOR}\n'
                        f'   Brauzer ochiq — o\'zingiz kiriting, keyin Enter bosing.'
                    )
                )
                input('\n[Enter] bosing: ')

            # ── 3-bosqich: OTP sahifasi paydo bo'lishini kutish ───────────
            try:
                await page.wait_for_selector(
                    OTP_SELECTORS[0], timeout=30_000
                )
                self.stdout.write(self.style.SUCCESS('  → SMS kod kiritish sahifasi ochildi!'))
            except Exception:
                self.stdout.write('  ⚠️  OTP inputi topilmadi, davom etamiz...')

            # ── 4-bosqich: SMS kodni terminalda so'rab, brauzerga kiritish ─
            otp = ''
            while len(otp) != 5 or not otp.isdigit():
                otp = input('\n📱 Telefoningizga kelgan 5 ta SMS kodni kiriting: ').strip()
                if len(otp) != 5 or not otp.isdigit():
                    self.stderr.write('❌ 5 ta raqam kiriting.')

            self.stdout.write(f'  → SMS kod brauzerga kiritilmoqda...')
            try:
                for i, selector in enumerate(OTP_SELECTORS):
                    el = await page.wait_for_selector(selector, timeout=5_000)
                    await el.click()
                    await page.keyboard.press(str(otp[i]))
                    await page.wait_for_timeout(100)

                self.stdout.write('  → OTP kiritildi, tasdiqlanmoqda...')
                # 2 ta login__actions-submit bor: birinchisi (PINFL) yashirin,
                # ikkinchisi ("Войти") ko'rinadi — .last() ishlatamiz
                otp_btn = page.locator(OTP_SUBMIT_SELECTOR).last
                await otp_btn.wait_for(state='visible', timeout=10_000)
                await otp_btn.click()
                await page.wait_for_load_state('networkidle', timeout=15_000)

            except Exception as exc:
                self.stderr.write(
                    self.style.WARNING(
                        f'\n⚠️  OTP avtomatik kiritib bo\'lmadi: {exc}\n'
                        f'   Brauzerda o\'zingiz kiriting, keyin Enter bosing.'
                    )
                )
                input('[Enter] bosing: ')

            # ── 5-bosqich: Login natijasini tekshirish ────────────────────
            await page.wait_for_timeout(2000)
            current_url = page.url
            self.stdout.write(f'  → Joriy URL: {current_url}')

            # /auth/login da qolsa — login bo'lmagan
            # /auth/role-selection yoki boshqa URL — login muvaffaqiyatli
            if LOGIN_SUCCESS_URL_PART in current_url and 'role-selection' not in current_url:
                self.stderr.write(
                    self.style.WARNING(
                        f'\n⚠️  Hali login sahifasidasiz: {current_url}\n'
                        '   Login bo\'lgach Enter bosing yoki q+Enter bilan chiqing.'
                    )
                )
                answer = input('[Enter] davom etish | [q+Enter] bekor qilish: ').strip()
                if answer.lower() == 'q':
                    await browser.close()
                    return

            # ── 6-bosqich: Session ni saqlash ─────────────────────────────
            storage_state = await context.storage_state()
            await browser.close()

            # DB ni async kontekstdan chaqirish uchun sync_to_async kerak
            from asgiref.sync import sync_to_async
            from apps.dmed_sync.models import DMEDSession
            await sync_to_async(DMEDSession.save_state)(storage_state, logged_in_by=by_user)

            self.stdout.write(self.style.SUCCESS(
                '\n✅ DMED session saqlandi!\n'
                '   Sinxronizatsiya avtomatik ishlaydi.\n'
                '   Monitoring: http://localhost:8000/dmed/\n'
            ))
