"""
DMED Playwright yordamchi funksiyalar — patient.py va visit.py uchun umumiy.
"""
import json as _json
import logging

from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')

JSHSHIR_MASK_SELECTOR = 'input[data-maska="##############"]'


async def _activate_hidden_panel(page: Page):
    """
    Hidden JSHSHIR input ning parent tab/pane ni topib aktive qiladi.
    Agar tab topilmasa, element ni to'g'ridan ko'rinadigan qiladi.
    """
    await page.evaluate(r"""
        (function() {
            const inp = document.querySelector('input[data-maska="##############"]');
            if (!inp) return;

            // 1. Radio yoki button topib JSHSHIR ni tanlaymiz
            const allInputs = document.querySelectorAll('input[type="radio"], button, .el-tabs__item, .el-radio__label');
            for (const el of allInputs) {
                const text = (el.textContent || el.value || '').toLowerCase();
                if (text.includes('jshshir') || text.includes('pinfl') || text.includes('hujjat')) {
                    el.click();
                    break;
                }
            }

            // 2. Parent tab-pane ni topib, mos tab header ni bosamiz
            let el = inp.parentElement;
            while (el && el !== document.body) {
                if (el.classList.contains('el-tab-pane')) {
                    const paneId = el.id;
                    if (paneId) {
                        const tabName = paneId.replace('pane-', '');
                        const tabHeader =
                            document.querySelector('[aria-controls="' + paneId + '"]') ||
                            document.getElementById('tab-' + tabName);
                        if (tabHeader && !tabHeader.classList.contains('is-active')) {
                            tabHeader.click();
                            return;
                        }
                    }
                    // Fallback: to'g'ridan ko'rinadigan qilamiz
                    el.style.display = 'block';
                    el.style.visibility = 'visible';
                    return;
                }
                el = el.parentElement;
            }
        })()
    """)
    await page.wait_for_timeout(600)


async def fill_jshshir_and_search(page: Page, jshshir: str, patient_pk: int):
    """
    JSHSHIR kiritib qidiruv tugmasini bosadi.
    Hidden bo'lsa JS yordamida ishlatadi.
    Topilmasa ValueError ko'taradi.
    """
    jshshir_input = page.locator(JSHSHIR_MASK_SELECTOR).first

    # 1. Elementni kutish (hidden bo'lsa ham attached)
    await jshshir_input.wait_for(state='attached', timeout=12_000)

    # 2. Panel/tabni aktivlashtirish
    await _activate_hidden_panel(page)

    # 3. Visible bo'lishini kutish (5s), bo'lmasa JS fallback
    try:
        await jshshir_input.wait_for(state='visible', timeout=5_000)
        await jshshir_input.click()
        await page.keyboard.press('Control+a')
        await page.keyboard.type(jshshir)
    except Exception:
        logger.warning(f'#{patient_pk}: JSHSHIR input hidden — JS bilan to\'ldiramiz')
        await page.evaluate(f"""
            (function() {{
                const inp = document.querySelector({_json.dumps(JSHSHIR_MASK_SELECTOR)});
                if (!inp) return;
                const setter = Object.getOwnPropertyDescriptor(
                    window.HTMLInputElement.prototype, 'value'
                ).set;
                setter.call(inp, {_json.dumps(jshshir)});
                inp.dispatchEvent(new Event('input',  {{bubbles: true}}));
                inp.dispatchEvent(new Event('change', {{bubbles: true}}));
            }})();
        """)
    await page.wait_for_timeout(300)

    # 4. Qidiruv tugmasi — visible yoki JS click
    try:
        search_btn = page.locator(
            '.select-patient-form__search-btns .el-button--primary'
        ).first
        await search_btn.wait_for(state='visible', timeout=5_000)
        await search_btn.click()
    except Exception:
        logger.warning(f'#{patient_pk}: search button hidden — JS click')
        await page.evaluate("""
            const btn = document.querySelector(
                '.select-patient-form__search-btns .el-button--primary'
            );
            if (btn) btn.click();
        """)

    # 5. Bemor ma'lumotlari chiqishini kutish
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
            f"Bemor #{patient_pk} DMED'da topilmadi (JSHSHIR: {jshshir})"
        )
