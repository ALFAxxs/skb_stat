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


@shared_task(bind=True, time_limit=660, soft_time_limit=600,
             name='dmed_sync.web_login', max_retries=0)
def dmed_web_login_task(self, pinfl: str, attempt_id: int, by_user: str = 'admin'):
    """Web UI orqali DMED login — headless Playwright."""
    from django.db import close_old_connections
    close_old_connections()  # Fork dan keyin eskirgan DB ulanishlarni tozalash
    asyncio.run(_login_flow(pinfl, attempt_id, by_user))


async def _set_status(attempt_id: int, status: str, error: str = ''):
    """DB holatini yangilash — run_in_executor orqali (thread deadlock yoq)."""
    from django.db import close_old_connections

    def _update():
        close_old_connections()
        from .models import DMEDLoginAttempt
        n = DMEDLoginAttempt.objects.filter(pk=attempt_id).update(
            status=status, error=error
        )
        logger.info(f'_set_status #{attempt_id} → {status} ({n} row updated)')

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _update)


async def _login_flow(pinfl: str, attempt_id: int, by_user: str):
    from playwright.async_api import async_playwright
    from .models import DMEDLoginAttempt, DMEDSession

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
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
            await page.goto(LOGIN_PAGE_URL, wait_until='domcontentloaded', timeout=30_000)
            await page.wait_for_timeout(1500)

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

            # ── 4. OTP sahifasini kutish (hidden bo'lsa ham attached) ─────────
            try:
                await page.wait_for_selector(
                    OTP_SELECTORS[0], state='attached', timeout=30_000
                )
            except Exception:
                pass  # sahifa allaqachon yuklangan bo'lishi mumkin

            await _set_status(attempt_id, 'waiting_otp')

            # ── 5. Frontend dan OTP ni kutish (max 5 daqiqa) ────────────────
            def _get_otp():
                from django.db import close_old_connections
                close_old_connections()
                from .models import DMEDLoginAttempt as _M
                row = _M.objects.values('otp_code').filter(pk=attempt_id).first()
                return row.get('otp_code', '') if row else ''

            otp_code = ''
            loop2 = asyncio.get_event_loop()
            for _ in range(150):   # 150 × 2s = 5 daqiqa
                otp_code = await loop2.run_in_executor(None, _get_otp)
                if otp_code:
                    break
                await asyncio.sleep(2)

            if not otp_code:
                await _set_status(attempt_id, 'failed', 'SMS kod 3 daqiqa ichida kiritilmadi')
                await browser.close()
                return

            # ── 6. OTP kiritish (JS orqali — hidden inputlar uchun) ──────────
            await _set_status(attempt_id, 'submitting')
            try:
                import json as _json
                otp_json = _json.dumps(otp_code)
                selectors_json = _json.dumps(OTP_SELECTORS)

                # OTP inputlari yashirin bo'lishi mumkin → JS bilan to'g'ridan qiymat
                await page.evaluate(f"""
                    (function() {{
                        const otp = {otp_json};
                        const sels = {selectors_json};
                        const setter = Object.getOwnPropertyDescriptor(
                            window.HTMLInputElement.prototype, 'value'
                        ).set;
                        sels.forEach((sel, i) => {{
                            const el = document.querySelector(sel);
                            if (!el) return;
                            setter.call(el, otp[i]);
                            el.dispatchEvent(new Event('input',  {{bubbles: true}}));
                            el.dispatchEvent(new Event('change', {{bubbles: true}}));
                        }});
                    }})();
                """)
                await page.wait_for_timeout(800)

                # Tasdiqlash tugmasi — ikkinchisi yoki birinchisi
                await page.evaluate("""
                    (function() {
                        const btns = document.querySelectorAll('button.login__actions-submit');
                        (btns[1] || btns[0]).click();
                    })();
                """)
                await page.wait_for_load_state('domcontentloaded', timeout=20_000)
                await page.wait_for_timeout(2000)
            except Exception as exc:
                await _set_status(attempt_id, 'failed', f'OTP kiritib bo\'lmadi: {exc}')
                await browser.close()
                return

            # ── 7. Session saqlash ───────────────────────────────────────────
            storage_state = await context.storage_state()
            await browser.close()

            def _save_session():
                from django.db import close_old_connections
                close_old_connections()
                from .models import DMEDSession as _S
                _S.save_state(storage_state, logged_in_by=by_user)

            await loop2.run_in_executor(None, _save_session)
            await _set_status(attempt_id, 'done')
            logger.info(f'DMED web login muvaffaqiyatli — {by_user}')

    except Exception as exc:
        import traceback
        logger.error(f'DMED web login kutilmagan xato: {traceback.format_exc()}')
        await _set_status(attempt_id, 'failed', str(exc)[:500])
