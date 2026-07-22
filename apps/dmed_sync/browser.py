"""
DMED Playwright browser sessiya boshqaruvi.

Login OTP (PINFL + SMS) talab qilgani uchun:
  - Birinchi marta: `python manage.py dmed_login`  → qo'lda login
  - Keyin: saqlanган storage_state orqali avtomatik ishlaydi
  - Session tugasa → Telegram xabar → qayta dmed_login
"""
from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from playwright.async_api import Page, BrowserContext

logger = logging.getLogger('dmed_sync')

DMED_URL = 'https://mis.dmed.uz'


async def _check_session(page: Page) -> bool:
    """
    Saqlangan cookies bilan mis.dmed.uz ochib, session aktiv ekanini tekshiradi.
    Login sahifasiga qaytib qolsa — session tugagan.
    """
    try:
        await page.goto(DMED_URL, wait_until='domcontentloaded', timeout=15_000)
        if '/auth/login' in page.url:
            return False
        return True
    except Exception as exc:
        logger.warning(f'Session tekshirish xatosi: {exc}')
        return False


async def _select_role(page: Page, role_name: str) -> bool:
    """
    /auth/role-selection sahifasida kerakli rolni tanlaydi.
    Karta matni bo'yicha qidiradi (masalan: 'Menejer', 'Laborant').
    """
    try:
        if '/auth/role-selection' not in page.url:
            await page.goto(DMED_URL + '/auth/role-selection',
                            wait_until='networkidle', timeout=15_000)
        # Karta matni bo'yicha topamiz — Element UI card ichidagi bold sarlavha
        card = page.locator(f'text={role_name}').first
        await card.wait_for(state='visible', timeout=10_000)
        await card.click()
        await page.wait_for_load_state('networkidle', timeout=15_000)
        logger.info(f'DMED rol tanlandi: {role_name} | URL: {page.url}')
        return True
    except Exception as exc:
        logger.error(f'Rol tanlab bo\'lmadi ({role_name}): {exc}')
        return False


async def _load_saved_state(context: BrowserContext) -> bool:
    """DB dan saqlangan session state ni contextga yuklaydi."""
    from .models import DMEDSession
    record = DMEDSession.get_latest()
    if not record or not record.storage_state_json or not record.is_valid:
        return False
    try:
        state = json.loads(record.storage_state_json)
        await context.add_cookies(state.get('cookies', []))
        return True
    except Exception as exc:
        logger.error(f'Session yuklab bo\'lmadi: {exc}')
        return False


async def _notify_session_expired():
    """Session tugaganda Telegram orqali admin ga xabar yuboradi."""
    from django.conf import settings
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    chat_id = getattr(settings, 'DMED_ALERT_CHAT_ID', '')  # .env da sozlanadi
    if not token or not chat_id:
        logger.warning('DMED session tugadi! Telegram chat_id sozlanmagan.')
        return
    try:
        import aiohttp
        text = (
            "⚠️ *DMED Session tugadi!*\n\n"
            "Sinxronizatsiya to'xtatildi.\n"
            "Qayta ulash uchun serverda:\n"
            "`python manage.py dmed_login`\n"
            "buyrug'ini ishga tushiring."
        )
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={
                'chat_id': chat_id,
                'text': text,
                'parse_mode': 'Markdown',
            })
    except Exception as exc:
        logger.error(f'Telegram xabar yuborib bo\'lmadi: {exc}')


@asynccontextmanager
async def dmed_session(role: str = ''):
    """
    Sinxronizatsiya uchun Playwright page qaytaradi.
    role — DMED dagi rol nomi (masalan 'Menejer', 'Laborant').
    Bo'sh qolsa settings.py dagi DMED_ROLE_MAP dan aniqlanadi.

    Ishlatish:
        async with dmed_session('Menejer') as page:
            await page.goto(DMED_URL + '/patients/new')
            ...
    """
    from playwright.async_api import async_playwright
    from .models import DMEDSession

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=getattr(settings, 'DMED_HEADLESS', True),
        )
        context: BrowserContext = await browser.new_context(
            viewport={'width': 1280, 'height': 900},
            locale='ru-RU',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            ),
        )

        loaded = await _load_saved_state(context)
        if not loaded:
            await browser.close()
            await _notify_session_expired()
            raise RuntimeError(
                'DMED session topilmadi. '
                'Avval `python manage.py dmed_login` buyrug\'ini ishga tushiring.'
            )

        page: Page = await context.new_page()

        if not await _check_session(page):
            DMEDSession.objects.filter(pk__gt=0).update(is_valid=False)
            await browser.close()
            await _notify_session_expired()
            raise RuntimeError(
                'DMED session muddati tugagan. '
                'Qayta kirish uchun `python manage.py dmed_login` ishga tushiring.'
            )

        # Rol tanlash — role-selection sahifasiga qaytishi mumkin
        if role:
            if not await _select_role(page, role):
                logger.warning(f'Rol tanlanmadi: {role}, davom etamiz...')

        try:
            yield page
        finally:
            await browser.close()
