"""
Web UI orqali DMED login — Celery task.

Jarayon:
  1. Headless brauzer ochiladi
  2. PINFL kiritiladi, "Kodni olish" bosiladi
  3. Status → waiting_otp (frontend OTP formni ko'rsatadi)
  4. DB da otp_code paydo bo'lgunicha 2s da bir marta tekshiriladi (max 3 daqiqa)
  5. OTP kiritiladi, login tasdiqlanadi
  6. Session DB ga saqlanadi, status → done
"""
import asyncio
import logging

from asgiref.sync import sync_to_async
from celery import shared_task

logger = logging.getLogger('dmed_sync')

LOGIN_PAGE_URL       = 'https://mis.dmed.uz/auth/login'
APP_TAB_SELECTOR     = '#tab-app'
PINFL_SELECTOR       = 'input[data-maska="##############"]'
OTP_SELECTORS        = [
    'input.login-page__otp-input.one',
    'input.login-page__otp-input.two',
    'input.login-page__otp-input.three',
    'input.login-page__otp-input.four',
    'input.login-page__otp-input.five',
]
OTP_SUBMIT_SELECTOR  = 'button.login__actions-submit'


@shared_task(bind=True, time_limit=300, soft_time_limit=270,
             name='dmed_sync.web_login', max_retries=0)
def dmed_web_login_task(self, pinfl: str, attempt_id: int, by_user: str = 'admin'):
    """Web UI orqali DMED login — headless Playwright."""
    asyncio.run(_login_flow(pinfl, attempt_id, by_user))


async def _set_status(attempt_id: int, status: str, error: str = ''):
    from .models import DMEDLoginAttempt
    await sync_to_async(
        lambda: DMEDLoginAttempt.objects.filter(pk=attempt_id).update(
            status=status, error=error
        )
    )()


async def _login_flow(pinfl: str, attempt_id: int, by_user: str):
    from playwright.async_api import async_playwright
    from .models import DMEDLoginAttempt, DMEDSession

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, slow_mo=150)
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 900},
                locale='ru-RU',
                user_agent=(
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0.0.0 Safari/537.36'
                ),
            )
            page = await context.new_page()

            # ── 1. Login sahifasini ochish ───────────────────────────────────
            await _set_status(attempt_id, 'opening')
            await page.goto(LOGIN_PAGE_URL, wait_until='networkidle', timeout=30_000)

            # ── 2. "DMED Pro ilovasi" tabiga bosish ─────────────────────────
            try:
                await page.wait_for_selector(APP_TAB_SELECTOR, timeout=8_000)
                await page.click(APP_TAB_SELECTOR)
                await page.wait_for_timeout(500)
            except Exception as exc:
                logger.warning(f'DMED tab topilmadi: {exc}')

            # ── 3. PINFL kiritish ────────────────────────────────────────────
            try:
                await page.wait_for_selector(PINFL_SELECTOR, timeout=10_000)
                await page.click(PINFL_SELECTOR)
                await page.keyboard.press('Control+a')
                await page.keyboard.type(pinfl, delay=80)
                await page.wait_for_timeout(500)
                await page.evaluate(
                    "document.querySelectorAll('button.login__actions-submit')[0].click()"
                )
            except Exception as exc:
                await _set_status(attempt_id, 'failed', f'PINFL kiritib bo\'lmadi: {exc}')
                await browser.close()
                return

            # ── 4. OTP sahifasini kutish ─────────────────────────────────────
            try:
                await page.wait_for_selector(OTP_SELECTORS[0], timeout=30_000)
            except Exception:
                pass  # sahifa allaqachon yuklangan bo'lishi mumkin

            await _set_status(attempt_id, 'waiting_otp')

            # ── 5. Frontend dan OTP ni kutish (max 3 daqiqa) ────────────────
            otp_code = ''
            for _ in range(90):
                row = await sync_to_async(
                    lambda: DMEDLoginAttempt.objects.values('otp_code')
                            .filter(pk=attempt_id).first()
                )()
                if row and row.get('otp_code'):
                    otp_code = row['otp_code']
                    break
                await asyncio.sleep(2)

            if not otp_code:
                await _set_status(attempt_id, 'failed', 'SMS kod 3 daqiqa ichida kiritilmadi')
                await browser.close()
                return

            # ── 6. OTP kiritish ──────────────────────────────────────────────
            await _set_status(attempt_id, 'submitting')
            try:
                for i, selector in enumerate(OTP_SELECTORS):
                    el = await page.wait_for_selector(selector, timeout=5_000)
                    await el.click()
                    await page.keyboard.press(str(otp_code[i]))
                    await page.wait_for_timeout(120)

                otp_btn = page.locator(OTP_SUBMIT_SELECTOR).last
                await otp_btn.wait_for(state='visible', timeout=10_000)
                await otp_btn.click()
                await page.wait_for_load_state('networkidle', timeout=20_000)
            except Exception as exc:
                await _set_status(attempt_id, 'failed', f'OTP kiritib bo\'lmadi: {exc}')
                await browser.close()
                return

            # ── 7. Session saqlash ───────────────────────────────────────────
            storage_state = await context.storage_state()
            await browser.close()

            await sync_to_async(DMEDSession.save_state)(storage_state, logged_in_by=by_user)
            await _set_status(attempt_id, 'done')
            logger.info(f'DMED web login muvaffaqiyatli — {by_user}')

    except Exception as exc:
        import traceback
        logger.error(f'DMED web login kutilmagan xato: {traceback.format_exc()}')
        await _set_status(attempt_id, 'failed', str(exc)[:500])
