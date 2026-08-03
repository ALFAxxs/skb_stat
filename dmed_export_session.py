"""
DMED sessiyasini lokal kompyuterdan eksport qilish.

Ishlatish (Windows, loyiha papkasida):
    python dmed_export_session.py

Keyin chiqgan JSON ni saytda /dmed/login/ sahifasiga joylashtiring.
"""
import asyncio
import json
import sys
from pathlib import Path


async def main():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("Playwright o'rnatilmagan.")
        print("  pip install playwright")
        print("  playwright install chromium")
        sys.exit(1)

    print("\n" + "=" * 55)
    print("  DMED Session Eksport — lokal kompyuter")
    print("=" * 55)
    print("\nBrauzer ochilmoqda...")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            slow_mo=150,
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
        await page.goto('https://mis.dmed.uz/auth/login',
                        wait_until='domcontentloaded', timeout=30_000)

        print("\n✅ Brauzer ochildi: https://mis.dmed.uz/auth/login")
        print("\nQuyidagi amallarni bajaring:")
        print("  1. 'DMED Pro ilovasi' tabiga bosing")
        print("  2. PINFL kiriting va 'Kodni olish' bosing")
        print("  3. Telefoningizga kelgan SMS kodni kiriting")
        print("  4. Tizimga muvaffaqiyatli kirgandan so'n...")
        print("     bu terminalga qaytib Enter bosing")
        print("\n" + "-" * 55)
        input("  [ENTER] — tizimga kirdim: ")

        print("\nSession saqlanmoqda...")
        state = await context.storage_state()
        await browser.close()

    output_path = Path(__file__).parent / 'dmed_session.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False)

    size_kb = output_path.stat().st_size // 1024
    print(f"\n✅ Session saqlandi: {output_path}  ({size_kb} KB)")
    print("\nKeyingi qadam:")
    print("  1. Saytda /dmed/login/ sahifasini oching")
    print("  2. 'Sessiyani qo'lda yuklash' bo'limini toping")
    print("  3. dmed_session.json faylini yuklang yoki ichidagi JSON ni joylashtiring")
    print("\n" + "=" * 55)


asyncio.run(main())
