# apps/contracts/utils.py

import io
import os
from datetime import date

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, Image, KeepTogether, PageBreak
)
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def _register_fonts():
    # O'zbek harflarini qo'llab-quvvatlaydigan fontlar (ustuvorlik tartibi)
    font_paths = [
        # Linux - DejaVuSerif (o'zbek harflari to'liq qo'llab-quvvatlanadi)
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        # Windows
        "C:/Windows/Fonts/times.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    bold_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "C:/Windows/Fonts/timesbd.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ]
    reg  = next((p for p in font_paths if os.path.exists(p)), None)
    bold = next((p for p in bold_paths if os.path.exists(p)), None)
    try:
        if reg:  pdfmetrics.registerFont(TTFont('TNR', reg))
        if bold: pdfmetrics.registerFont(TTFont('TNR-Bold', bold))
        return bool(reg)
    except Exception:
        return False


def generate_qr_code_image(url: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf


def generate_contract_pdf(contract) -> bytes:
    patient   = contract.patient_card
    has_times = _register_fonts()
    FN        = 'TNR'      if has_times else 'Times-Roman'
    FB        = 'TNR-Bold' if has_times else 'Times-Bold'

    address_parts = [
        str(patient.country)  if patient.country  else '',
        str(patient.region)   if patient.region   else '',
        str(patient.district) if patient.district else '',
        str(patient.city)     if patient.city     else '',
        patient.street_address or '',
    ]
    full_address = ', '.join(p for p in address_parts if p) or '-'

    from django.conf import settings
    base_url   = getattr(settings, 'SITE_URL', 'https://markaziyklinikkasalxona-statistika.uz')
    verify_url = f"{base_url}/contracts/verify/{contract.verify_token}/"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=20*mm, leftMargin=25*mm, topMargin=20*mm, bottomMargin=25*mm)
    W = A4[0] - 45*mm

    def S(name, **kw):
        kw.setdefault('fontName', FN)
        kw.setdefault('fontSize', 11)
        kw.setdefault('leading', 14)
        return ParagraphStyle(name, **kw)

    sC  = S('c', alignment=TA_CENTER)
    sL  = S('l', alignment=TA_LEFT)
    sJ  = S('j', alignment=TA_JUSTIFY)
    sBc = S('bc', alignment=TA_CENTER, fontName=FB, fontSize=12)
    sB  = S('b',  fontName=FB, fontSize=11)
    sBs = S('bs', fontName=FB, fontSize=11, spaceBefore=5)
    sSc = S('sc', fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor('#555'))
    sQ  = S('q',  fontSize=9, leading=13)

    def p(text, st=None): return Paragraph(text, st or sJ)
    def sp(h=4): return Spacer(1, h*mm)
    def hr(): return HRFlowable(width="100%", thickness=0.5, color=colors.black)

    cd  = contract.contract_date.strftime('%d.%m.%Y') if contract.contract_date else date.today().strftime('%d.%m.%Y')
    bds = patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else '______'
    pp  = patient.passport_serial or '______'
    jsh = f", JSHSHIR: <u>{patient.JSHSHIR}</u>" if patient.JSHSHIR else ''
    tel = patient.phone or '______'

    story = [
        p(f"<b>{contract.contract_number} sonli shartnoma</b>", sBc),
        p("Pullik tibbiy yordam ko'rsatish bo'yicha", sC),
        sp(3),
        p(f"Toshkent sh. {'&nbsp;'*80} <u>{cd}</u>", sL),
        sp(3),
        p(f'<b>"Temir yo`l ijtimoiy xizmatlar" MCHJ Markaziy klinik kasalxona filiali</b> '
          f'Ishonchnoma asosida ish yurituvchi direktor I.K.Yangiboyev nomidan '
          f'keyingi o`rinlarda <b>"Ijrochi"</b> deb ataladi, va'),
        sp(2),
        p(f'<u>{full_address}</u>', sC),
        p('(yashash joyi)', sSc),
        sp(2),
        p(f'manzilida yashovchi, pasport/ID: <u>&nbsp;{pp}&nbsp;</u>{jsh} '
          f'ikkinchi tomondan, keyingi o`rinlarda <b>"Bemor"</b> deb ataladi, '
          f"mazkur shartnomani quyidagilar to'g'risida tuzdilar:"),
        sp(3), hr(), sp(2),
    ]

    # 1-2 bandlar
    story += [
        p('<b>1. SHARTNOMA MAVZUSI.</b>', sBs),
        p("&nbsp;&nbsp;&nbsp;&nbsp;Tasdiqlangan preyskurantga muvofiq pullik tibbiy-diagnostika xizmatlarini ko'rsatish."),
        sp(2),
        p('<b>2. SHARTNOMANING BAHOSI VA HISOB-KITOB TARTIBI.</b>', sBs),
        p("&nbsp;&nbsp;&nbsp;&nbsp;Joriy shartnoma narxi pullik tibbiy diagnostic xizmatlarni ko'rsatish iborat <b>QQS bilan</b>."),
        p("&nbsp;&nbsp;&nbsp;&nbsp;To'lov \"Bemor\" tomonidan shartnoma narxining 100% miqdorida oldindan to'lov yo'li bilan 3 bank kuni ichida amalga oshiriladi."),
        sp(2),
    ]

    # 3-band
    story.append(p('<b>3. TOMONLARNING HUQUQ VA MAJBURIYATLARI.</b>', sBs))
    for side, items in [
        ('"Ijrochi"ning majburiyatlari:', [
            "Shartnoma tuzilgan kundan qat'iy nazar, bo'sh joylar mavjud bo'lgan taqdirda tibbiy amaliyotni yuqori saviyada amalga oshirish.",
            "Foydalanilmagan mablag'larni bemorga qaytarish.",
            "Tibbiy xizmatlar, dori-darmonlar uchun hisob-fakturani taqdim etish.",
            "Xizmatlarni qabul qilish dalolatnomasini o'z vaqtida tuzish va imzolash.",
            "Bemorning sog'ligi haqidagi tibbiy sirlarni oshkor qilmaslik.",
        ]),
        ('"Ijrochi" quyidagi huquqlarga ega:', [
            "Bemor majburiyatlariga rioya qilmagan holda shartnomani bir tomonlama bekor qilish.",
            "Bemordan yetkazilgan zararlarni to'liq hajmda qoplashni talab qilish.",
        ]),
        ('"Bemor"ning majburiyatlari:', [
            "Ijrochining ichki tartib-qoidalariga va tibbiy xodimlarning tayinlashlariga rioya qilish.",
            "Xizmatlarning to'liq narxini o'z vaqtida to'lash.",
            "Yetkazilgan zararlarni to'liq qoplash.",
        ]),
        ('"Bemor" quyidagi huquqlarga ega:', [
            "Tartib-qoidalar, diagnostika va davolash standartlari hamda tariflar bilan tanishish.",
            "Foydalanilmagan mablag'larning qaytarilishi.",
            "Ushbu shartnomani bir tomonlama bekor qilish.",
        ]),
    ]:
        story.append(p(f'&nbsp;&nbsp;&nbsp;&nbsp;<b>{side}</b>'))
        for item in items:
            story.append(p(f'&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;- {item}'))
        story.append(sp(1))

    # 4-7 bandlar
    for title, items in [
        ("4. TOMONLARNING KORRUPSIYAGA QARSHI KURASHISH BO'YICHA MAJBURIYATLARI", [
            "4.1. Tomonlar korrupsiyaga qarshi kurashish bo'yicha qoidalarga rioya qilish majburiyatini oladilar.",
            "4.2. Tomonlar bir-birini ishonch telefoni orqali xabardor qilish majburiyatini oladi.",
            "4.3. Talablar bajarilmaganda shartnoma bir tomonlama bekor qilinishi mumkin.",
        ]),
        ("5. TOMONLARNING JAVOBGARLIGI.", [
            "5.1. Tomonlar o'z vazifalarini lozim darajada bajarmagan taqdirda O'zbekiston Respublikasi qonunchiligiga muvofiq javobgar bo'ladilar.",
            "Favqulotda vaziyatlarda (tabiiy ofatlar, harbiy harakatlar) tomonlar javobgarlikdan ozod etiladi.",
        ]),
        ("6. NIZOLARNI HAL ETISH TARTIBI.", [
            "Nizolar, iloji bo'lsa, tomonlar o'rtasidagi muzokaralar orqali hal qilinadi.",
            "Agar muzokaralar yo'li bilan hal qilishning iloji bo'lmasa, ular sudda hal qilinadi.",
        ]),
        ("7. SHARTNOMANING BOSHQA SHARTLARI.", [
            "7.1. Qo'shimcha xarajatlar alohida haq to'lanadi.",
            "7.2. Tartibga solinmagan masalalarda O'zbekiston Respublikasi qonunchiligiga amal qilinadi.",
            "7.3. O'zgartishlar ikkala tomon imzolagan taqdirda amal qiladi.",
            "7.4. Shartnoma imzolangan paytdan boshlab kuchga kiradi.",
            "7.5. Shartnoma har bir tomon uchun ikki nusxada tuziladi.",
            "7.6. Xizmatlar qabul qilish dalolatnomasi imzolanganidan keyin ko'rsatilgan hisoblanadi.",
        ]),
    ]:
        story.append(p(f'<b>{title}</b>', sBs))
        for item in items:
            story.append(p(f'&nbsp;&nbsp;&nbsp;&nbsp;{item}'))
        story.append(sp(1))

    story += [sp(2), hr(), sp(2)]
    story.append(p('<b>8. TOMONLARNING HUQUQIY MANZILLARI</b>', sBs))
    story.append(sp(2))

    cw = W / 2 - 3*mm
    sign_table = Table([[
        Paragraph('<b>IJROCHI</b>', sB),
        Paragraph('<b>BEMOR</b>', sB),
    ],[
        Paragraph(
            '"Temir yo`l ijtimoiy xizmatlar" MCHJ<br/>'
            'Markaziy klinik kasalxona filiali<br/><br/>'
            "O'zbekiston Respublikasi, 100047,<br/>"
            'Toshkent shahar, Yashnobod tumani,<br/>'
            'Taraqqiyot 2 tor, 12A uy.<br/><br/>'
            'X/R. 2020 8000 9041 5940 6010<br/>'
            "O'zbekiston Milliy banki, Mirobod filiali<br/>"
            'MFO 00450. STIR 203855194<br/><br/>'
            'Tel. (+99871) 299-63-02, 299-62-07<br/><br/>'
            'Direktor ____________ I.K.Yangiboyev', sL),
        Paragraph(
            f'F.I.Sh: <u>&nbsp;{patient.full_name}&nbsp;</u><br/><br/>'
            f"Tug'ilgan sana: <u>&nbsp;{bds}&nbsp;</u><br/><br/>"
            f'Pasport/ID: <u>&nbsp;{pp}&nbsp;</u><br/><br/>'
            + (f'JSHSHIR: <u>&nbsp;{patient.JSHSHIR}&nbsp;</u><br/><br/>' if patient.JSHSHIR else '')
            + f'Manzil: <u>&nbsp;{full_address}&nbsp;</u><br/><br/>'
            f'Tel: <u>&nbsp;{tel}&nbsp;</u><br/><br/><br/>'
            f'Imzo: _______________________', sL),
    ]], colWidths=[cw, cw])
    sign_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LINEAFTER', (0,0), (0,-1), 0.5, colors.lightgrey),
        ('FONTNAME', (0,0), (-1,-1), FN),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
    ]))
    # Imzo + QR blokni bitta sahifada saqlash
    qr_buf = generate_qr_code_image(verify_url)
    qr_img = Image(qr_buf, width=25*mm, height=25*mm)
    qr_table = Table([[
        qr_img,
        Paragraph(
            f"<b>Shartnomani onlayn tekshirish uchun QR kodni skaner qiling</b><br/><br/>"
            f"Shartnoma No. {contract.contract_number} | Sana: {cd}",
            sQ
        ),
    ]], colWidths=[30*mm, W-30*mm])
    qr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9f9f9')),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))

    # Imzo jadvali va QR kodni bitta blokda saqlash — ajralmasin
    story.append(KeepTogether([
        sign_table,
        sp(6),
        qr_table,
    ]))

    doc.build(story)
    return buf.getvalue()