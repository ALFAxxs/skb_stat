# apps/patients/transliteration.py
"""
Kirill (o'zbekcha) matnni lotin yozuviga o'giradigan yordamchi.

Faqat kirill harflarini almashtiradi — lotin harflar, raqamlar, belgilar
(qavs, tire, nuqta va h.k.) tegilmay qoladi. Shu sababli bitta katakda
lotin va kirill aralash kelgan holatlarni ham to'g'ri o'giradi
(masalan: "TEMIRYO'LINFRATUZILMA АЖ (00085)" -> "TEMIRYO'LINFRATUZILMA AJ (00085)").

Diqqat — avtomatik o'girish quyidagilarni TUZATA OLMAYDI:
  - Manba matnida ў/қ/ғ/ҳ o'rniga oddiy у/к/г/х yozilgan bo'lsa (klaviaturada
    maxsus harflar bo'lmagani uchun tez-tez uchraydi), natija ham xato
    qoladi ("минтакавий" -> "mintakaviy", to'g'risi "mintaqaviy" bo'lishi
    kerak edi). Buni faqat lug'at asosida yoki qo'lda tekshirib tuzatish
    mumkin, sof transliteratsiya vazifasi emas.
  - Rus tilidagi tayyor qisqartmalar (ПЧ, ШЧ, ЭЧ, ТЧ kabi temir yo'l
    kodlari) harf-harflab o'giriladi (ПЧ -> PCH), tarjima qilinmaydi.
"""

import re

# Kirillcha kichik harf -> lotincha (rasmiy o'zbek alifbosi, 2021-yilgi jadval).
# Ц -> S (rasmiy jadvalga ko'ra); agar "Ts" kerak bo'lsa shu qatorni o'zgartiring.
_SIMPLE_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
    'ё': 'yo', 'ж': 'j', 'з': 'z', 'и': 'i', 'й': 'y',
    'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
    'ф': 'f', 'х': 'x', 'ц': 's', 'ч': 'ch', 'ш': 'sh',
    'щ': 'sh', 'ъ': "'", 'ы': 'i', 'ь': '', 'э': 'e',
    'ю': 'yu', 'я': 'ya',
    # O'zbekchaga xos harflar
    'ў': "o'", 'қ': 'q', 'ғ': "g'", 'ҳ': 'h',
}
# 'е' alohida — pozitsiyaga qarab "ye" yoki "e" bo'ladi (pastda hal qilinadi)
_YE_SOUND = 'ye'
_E_SOUND = 'e'

_CYRILLIC_RE = re.compile('[а-яА-ЯёЁўЎқҚғҒҳҲ]')
_VOWELS = set('аеёиоуыэюяўАЕЁИОУЫЭЮЯЎ')


def _is_cyrillic_letter(ch: str) -> bool:
    return bool(_CYRILLIC_RE.match(ch))


def _apply_case(latin: str, is_upper: bool, is_caps_run: bool) -> str:
    if not latin:
        return latin
    if is_caps_run:
        return latin.upper()
    if is_upper:
        return latin[0].upper() + latin[1:]
    return latin


def cyrillic_to_latin(text: str) -> str:
    """Matndagi kirill harflarini lotinga o'giradi, qolgan hamma narsani (lotin
    harflar, raqamlar, belgilar) o'zgarishsiz qoldiradi."""
    if not text:
        return text

    result = []
    for i, ch in enumerate(text):
        lower = ch.lower()
        if lower not in _SIMPLE_MAP and lower != 'е':
            result.append(ch)
            continue

        is_upper = ch.isupper()
        prev_ch = text[i-1] if i > 0 else ''
        # Katta harflar ketma-ketligi ichidami (qisqartma: "АЖ", "ПЧ-1")
        # — oldingi YOKI keyingi harf ham katta bo'lsa, caps-run deb hisoblanadi
        # (oldingi tekshiruv qisqartmaning oxirgi harfini — masalan "Ч" ni
        # "ПЧ-1" da — to'g'ri aniqlash uchun kerak, chunki undan keyin harf yo'q).
        next_letter = next((c for c in text[i+1:i+3] if c.isalpha()), '')
        prev_alpha_upper = prev_ch.isalpha() and prev_ch.isupper()
        next_alpha_upper = next_letter.isupper() if next_letter else False
        is_caps_run = is_upper and (prev_alpha_upper or next_alpha_upper)

        if lower == 'е':
            at_boundary = (prev_ch == '') or (not prev_ch.isalpha()) or (prev_ch.lower() in _VOWELS) or (prev_ch.lower() in ('ъ', 'ь'))
            latin = _YE_SOUND if at_boundary else _E_SOUND
        else:
            latin = _SIMPLE_MAP[lower]

        result.append(_apply_case(latin, is_upper, is_caps_run))

    return ''.join(result)


def has_cyrillic(text: str) -> bool:
    return bool(text) and bool(_CYRILLIC_RE.search(text))
