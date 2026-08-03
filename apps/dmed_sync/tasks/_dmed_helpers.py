"""
DMED Playwright yordamchi funksiyalar.
Barcha DOM interaksiyalar JS orqali — visibility tekshiruvi yo'q.
"""
import json as _json
import logging

from playwright.async_api import Page

logger = logging.getLogger('dmed_sync')

JSHSHIR_MASK_SELECTOR = 'input[data-maska="##############"]'


async def fill_jshshir_and_search(page: Page, jshshir: str, patient_pk: int):
    """
    JSHSHIR kiritib qidiruv tugmasini bosadi.
    Hammasi JS orqali — hidden/visible farqi yo'q.
    """
    await page.wait_for_timeout(1000)

    # Sahifa to'g'ri ekanini tekshirish
    current_url = page.url
    if 'role-selection' in current_url or '/auth/login' in current_url:
        raise RuntimeError(
            f"Bemor #{patient_pk}: to'g'ri sahifaga o'ta olmadi. "
            f"URL: {current_url}. DMED session muddati tugagan bo'lishi mumkin."
        )

    # JSHSHIR input mavjudligini tekshirish
    inp_exists = await page.evaluate(
        f"!!document.querySelector({_json.dumps(JSHSHIR_MASK_SELECTOR)})"
    )
    if not inp_exists:
        raise ValueError(
            f"Bemor #{patient_pk}: JSHSHIR input topilmadi. URL: {current_url}"
        )

    # Tab/panel ochish + JSHSHIR kiritish — hammasi bitta JS da
    await page.evaluate(f"""
        (function() {{
            const JSHSHIR = {_json.dumps(jshshir)};
            const inp = document.querySelector({_json.dumps(JSHSHIR_MASK_SELECTOR)});
            if (!inp) return;

            // 1. Radio/tab orqali JSHSHIR panelni ochishga urinish
            const triggers = [
                ...document.querySelectorAll(
                    '.el-tabs__item, .el-radio__label, label, button'
                )
            ];
            for (const t of triggers) {{
                const txt = (t.textContent || '').toLowerCase().trim();
                if (txt === 'jshshir' || txt === 'pinfl' || txt.includes('jshshir')) {{
                    t.click();
                    break;
                }}
            }}

            // 2. Parent el-tab-pane ni topib header ni bosish
            let el = inp.parentElement;
            while (el && el !== document.body) {{
                const isPane =
                    el.classList.contains('el-tab-pane') ||
                    el.getAttribute('role') === 'tabpanel';
                if (isPane) {{
                    const pId = el.id || '';
                    if (pId) {{
                        const hdr =
                            document.querySelector('[aria-controls="' + pId + '"]') ||
                            document.getElementById('tab-' + pId.replace('pane-', ''));
                        if (hdr) hdr.click();
                    }}
                    // Har qanday holatda to'g'ridan ko'rinadigan qilish
                    el.style.cssText += ';display:block!important;visibility:visible!important;';
                    break;
                }}
                el = el.parentElement;
            }}

            // 3. Vue reactive value setter
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value'
            ).set;
            setter.call(inp, JSHSHIR);
            inp.dispatchEvent(new Event('input',  {{bubbles: true}}));
            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
        }})();
    """)
    await page.wait_for_timeout(600)

    # Search tugmasini JS orqali bosish
    clicked = await page.evaluate("""
        (function() {
            // Selektor 1: standart joy
            let btn = document.querySelector(
                '.select-patient-form__search-btns .el-button--primary'
            );
            if (btn) { btn.click(); return true; }

            // Selektor 2: input ga yaqin primary button
            const inp = document.querySelector('input[data-maska="##############"]');
            if (!inp) return false;
            let p = inp.parentElement;
            while (p && p !== document.body) {
                btn = p.querySelector('button.el-button--primary');
                if (btn) { btn.click(); return true; }
                p = p.parentElement;
            }
            return false;
        })()
    """)
    if not clicked:
        raise ValueError(
            f"Bemor #{patient_pk}: JSHSHIR search tugmasi topilmadi (URL: {page.url})"
        )

    # Qidiruv natijasini kutish
    try:
        await page.wait_for_function(
            """() => {
                const btn = document.querySelector(
                    '.selected-patient-info .el-button.is-link'
                );
                return btn && !btn.disabled && btn.textContent.trim() !== '-';
            }""",
            timeout=20_000,
        )
    except Exception:
        # Screenshot saqlash — debugging uchun
        try:
            import tempfile, os
            path = os.path.join(tempfile.gettempdir(), f'dmed_notfound_{patient_pk}.png')
            await page.screenshot(path=path)
            logger.warning(f'Screenshot: {path}')
        except Exception:
            pass
        raise ValueError(
            f"Bemor #{patient_pk} DMED'da topilmadi (JSHSHIR: {jshshir})"
        )
