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
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerif.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
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
    # ── Sahifa chegaralarini kichraytirish ──
    doc = SimpleDocTemplate(buf, pagesize=A4,
        rightMargin=15*mm, leftMargin=18*mm, topMargin=12*mm, bottomMargin=12*mm)
    W = A4[0] - 33*mm

    # ── Font o'lchamlarini kamaytirish (server uchun) ──
    def S(name, **kw):
        kw.setdefault('fontName', FN)
        kw.setdefault('fontSize', 9.5)
        kw.setdefault('leading', 12)
        return ParagraphStyle(name, **kw)

    sC  = S('c',  alignment=TA_CENTER)
    sL  = S('l',  alignment=TA_LEFT)
    sJ  = S('j',  alignment=TA_JUSTIFY)
    sBc = S('bc', alignment=TA_CENTER, fontName=FB, fontSize=11)
    sB  = S('b',  fontName=FB, fontSize=9.5)
    sBs = S('bs', fontName=FB, fontSize=9.5, spaceBefore=3)
    sSc = S('sc', fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor('#555'))
    sQ  = S('q',  fontSize=8.5, leading=12)
    sJ1 = S('j1', alignment=TA_JUSTIFY, leftIndent=4*mm)
    sJ2 = S('j2', alignment=TA_JUSTIFY, leftIndent=8*mm)

    def p(text, st=None): return Paragraph(text, st or sJ)
    def sp(h=3): return Spacer(1, h*mm)
    def hr(): return HRFlowable(width="100%", thickness=0.5, color=colors.black)

    cd  = contract.contract_date.strftime('%d.%m.%Y') if contract.contract_date else date.today().strftime('%d.%m.%Y')
    bds = patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else '______'
    pp  = patient.passport_serial or '______'
    jsh = f", JSHSHIR: <u>{patient.JSHSHIR}</u>" if patient.JSHSHIR else ''
    tel = patient.phone or '______'

    story = [
        p(f"<b>{contract.contract_number} sonli shartnoma</b>", sBc),
        p("Pullik tibbiy yordam ko'rsatish bo'yicha", sC),
        sp(2),
        p(f"Toshkent sh. {'&nbsp;'*80} <u>{cd}</u>", sL),
        sp(2),
        p(f'<b>"Temir yo`l ijtimoiy xizmatlar" MCHJ Markaziy klinik kasalxona filiali nomidan</b> '
          f'Ishonchnoma asosida ish yurituvchi direktor I.K.Yangiboyev '
          f'keyingi o`rinlarda <b>"Ijrochi"</b> deb ataladi, va '
          f'{patient.full_name}'),
        sp(1),
        p(f'<u>{full_address}</u>', sC),
        p('(yashash joyi)', sSc),
        sp(1),
        p(f'manzilida yashovchi, pasport/ID: <u>&nbsp;{pp}&nbsp;</u>{jsh} '
          f'ikkinchi tomondan, keyingi o`rinlarda <b>"Bemor"</b> deb ataladi, '
          f"mazkur shartnomani quyidagilar to'g'risida tuzdilar:"),
        sp(2), hr(), sp(1),
    ]

    # 1-2 bandlar
    story += [
        p('<b>1. SHARTNOMA MAVZUSI.</b>', sBs),
        p("&nbsp;&nbsp;&nbsp;&nbsp;1.1 Tasdiqlangan preyskurantga muvofiq pullik tibbiy-diagnostika xizmatlarini ko'rsatish."),
        sp(1),
        p('<b>2. SHARTNOMANING BAHOSI VA HISOB-KITOB TARTIBI.</b>', sBs),
        p("&nbsp;&nbsp;&nbsp;&nbsp;2.1 Joriy shartnoma narxi pullik tibbiy diagnostik xizmatlarni ko'rsatish iborat <b>QQS bilan</b>."),
        p("&nbsp;&nbsp;&nbsp;&nbsp;2.2 To'lov \"Bemor\" tomonidan shartnoma narxining 100% miqdorida oldindan to'lov yo'li bilan 3 bank ish kuni ichida amalga oshiriladi."),
        sp(1),
    ]

    # 3-band
    story.append(p('<b>3. TOMONLARNING HUQUQ VA MAJBURIYATLARI.</b>', sBs))
    for side, items in [
        ('3.1. "Ijrochi"ning majburiyatlari:', [
            "3.1.1. Shartnoma tuzilgan kundan qatʼiy nazar, bo'sh joylar mavjud bo'lgan taqdirda va tibbiy amaliyotning yuqori saviyada, O'zbekiston Respublikasida, texnologiya va kasbiy etika hamda ushbu shartnomada belgilangan miqdorlarda va muddatlarda tibbiy xizmatlar ko'rsatish.",
            "3.1.2. Hisob-faktura bilan rasmiylashtirilgan xaqiqiy xarajatlar natijalari bo'yicha foydalanilmagan mablag'larni bemorga/homiyga (kerak emasini chizib tashlang) qaytarib berish.",
            "3.1.3. Bemorga taqdim etilgan tibbiy xizmatlar, dori-darmonlar va oziq-ovqat uchun hisob-fakturani bemorga/homiyga (kerak emasini chizib tashlang) taqdim etish.",
            "3.1.4. Xizmatlarni yetkazib berishni qabul qilish to`g'risidagi dalolatnomani o'z vaqtida tuzish va imzolash.",
            "3.1.5. Bemorning sog'ligi haqidagi tibbiy sirlarni oshkor qilmaslik.",
        ]),
        ('3.2. "Ijrochi" quyidagi huquqlarga ega:', [
            "3.2.1. Bemor majburiyatlariga rioya qilmagan holda ushbu shartnomani bir tomonlama bekor qilish.",
            "3.2.2. Bemordan moddiy zarar, bemorning aybi bilan yetkazilgan zararlarni to'liq hajmda qoplashni talab qilish va olish.",
        ]),
        ('3.3. "Bemor"ning majburiyatlari:', [
            "3.3.1. Ijrochining ichki tartib-qoidalariga, tibbiy xodimlarining davolash rejimiga va tayinlashlariga rioya qilish.",
            "3.3.2. Ijrochiga xizmatlarning to'liq narxini ushbu Shartnomaning 2.2. bandlarida nazarda tutilgan shartlarda o'z vaqtida to'lash.",
            "3.3.3. Ularga yetkazilgan zararlarni to'liq qoplash.",
        ]),
        ('3.4. "Bemor" quyidagi huquqlarga ega:', [
            "3.4.1. Tibbiy yordam ko'rsatish bo'yicha tasdiqlangan tartib-qoidalar, diagnostika va davolash standartlari hamda tariflar bilan tanishib chiqish.",
            "3.4.2. Hisob-faktura bo'yicha berilgan xaqiqiy xarajatlar natijalari asosida qolgan foydalanilmagan mablag'larning qaytarilishini talab qilish.",
            "3.4.3. Xizmatlarni yetkazib berishni qabul qilish dalolatnomasi mazmuni bilan kelishmovchilik yuzaga kelgan taqdirda, ushbu dalolatnomani mavjud izoxlar yozilgan xolda imzolash.",
            "3.4.4. Ushbu shartnomani bir tomonlama bekor qilish. Shartnoma bir tomonlama bekor qilingan taqdirda, bemorga ko'rsatilgan xizmatlarning haqiqiy xarajatlari olib qolinadi va qolgan qismi qaytarib beriladi",
        ]),
    ]:
        story.append(p(f'<b>{side}</b>', sJ1))
        for item in items:
            story.append(p(item, sJ2))
        story.append(sp(1))

    # 4-7 bandlar
    for title, items in [
        ("4. TOMONLARNING KORRUPSIYAGA QARSHI KURASHISH BO`YICHA MAJBURIYATLARI", [
            "4.1. Shartnoma bo`yicha o'z majburiyatlarini bajarishda tomonlar korrupsiyaga qarshi kurashish bo`yicha qoidalarga, shu jumladan amaldagi qonunlarga rioya etilishini ta`minlaydi, ya`ni tomonlar bir-biriga yoki davlat ishtirokidagi davlat xodimiga pora berish yoki pora berishda vositachilik qilish, moddiy yoki nomoddiy naf olishdan tiyilishi lozim. Tomonlar ushbu harakatlarning olidini olish bo`yicha chora-tadbirlar qabul qilinishini kafolatlaydi.",
            "4.2. Yoki ishonch telefoni orqali bir-birini xabardor qilish majburiyatini oladi. Bunda tomonlar yuzaga kelgan holatga oydinlik kiritish maqsadida yozma izoh talab qilish huquqiga ega va murojaatni olgan tomon 10 (o`n) ish kuni mobaynida tushuntirish berishi yoki o'z fikrini bildirishi mumkin.",
            "4.3. Mazkur bobning talablari bajarilmaganda, shu jumladan belgilangan muddatda korrupsion xavf-xatar bartaraf etilmasa, tomonlar amalaga oshirgan choralar korrupsion holatni pasayishiga olib kelmasa, boshqa tomon shartnomani bekor qilish huquqiga ega yoki uni ijrosini to`xtatib turish huquqiga ega.",
        ]),
        ("5. TOMONLARNING JAVOBGARLIGI.", [
            "5.1 Tomonlar ushbu shartnoma bo'yicha o'z vazifalarini lozim darajada bajarmagan taqdirda ular O'zbekiston Respublikasi qonun xujjatlariga muvofiq javobgar bo'ladilar.",
            "5.2 Shartnoma imzolangandan so'ng favqulotda vaziyat yuz berganida: tabiy ofatlar, xarbiy xarakatlar, terroristik aktlar, ommaviy tartibsizliklar va shu kabi favqulotda xolatlarning oqibatida shifoxonaning kunlik ish jarayoni buzilganda, tomonlar o'z majburiyatini bajarmaganligi uchun javobgarlikga tortilmaydi.",
        ]),
        ("6. NIZOLАRNI HAL ETISH TАRTIBI.", [
            "6.1. Ushbu shartnomani bajarishda yuzaga kelishi mumkin bo'lgan nizo va kelishmovchiliklar, iloji bo'lsa, tomonlar o'rtasidagi muzokaralar orqali xal qilinadi.",
            "6.2. Аgar nizolarni muzokaralar yo'li bilan hal qilishning iloji bo'lmasa, ular O'zbekiston Respublikasi qonunchiligiga muvofiq sudda ko'rib chiqiladi.",
        ]),
        ("7. SHАRTNOMАNING BOSHQА SHARTLАRI.", [
            "7.1. Bemorga qo'shimcha diagnostik va terapevtik yordam, dori-darmonlar va oziq-ovqat bilan taʼminlash xarajatlari, agar bemordagi yondosh kasalliklarni aniqlash munosabati bilan yuqorida aytib o'tilganlar talab qilingan bo'lsa, Bemor yoki Xomiy tomonidan ushbu shartnomaga qo'shimcha shartnoma asosida to'lanadi.",
            "7.2. Ushbu shartnoma bilan tartibga solinmagan masalalarda tomonlar O'zbekiston Respublikasi qonunchiligiga amal qiladilar.",
            "7.3. Ushbu shartnomaga kiritilgan har qanday o'zgartirish va qo'shimchalar amal qiladi va shartnomaning ajralmas qismini faqat ular yozma shaklda tuzilgan va vakolatli taraflarning vakillari tomonidan imzolangan taqdirda tashkil etadi.",
            "7.4. Bu shartnoma barcha tomonlar tomonidan imzolangan paytdan boshlab kuchga kiradi va davolanish tugagunga qadar amal qiladi.",
            "7.5. Bu shartnoma tomonlarning xar biri uchun bittadan ikki nusxada tuziladi. Barcha nusxalar bir xil va bir xil qonuniy kuchga ega.",
            "7.6. Xizmatlar Ijrochi va Bemor tomonidan xizmatga qabul qilish dalolatnomasi imzolanganidan keyin ko'rsatilgan hisoblanadi.",
        ]),
    ]:
        story.append(p(f'<b>{title}</b>', sBs))
        for item in items:
            story.append(p(item, sJ1))
        story.append(sp(1))

    # ── Imzo jadvali ──
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
        ('FONTSIZE', (0,0), (-1,-1), 9.5),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 3),
        ('RIGHTPADDING', (0,0), (-1,-1), 3),
    ]))

    # ── QR blok ──
    qr_buf = generate_qr_code_image(verify_url)
    qr_img = Image(qr_buf, width=22*mm, height=22*mm)
    qr_table = Table([[
        qr_img,
        Paragraph(
            f"<b>Shartnomani onlayn tekshirish uchun QR kodni skaner qiling</b><br/><br/>"
            f"Shartnoma No. {contract.contract_number} | Sana: {cd}",
            sQ
        ),
    ]], colWidths=[27*mm, W-27*mm])
    qr_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f9f9f9')),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))

    # ── 8-band: KeepTogether OLIB TASHLANDI ──
    story += [
        sp(2), hr(), sp(1),
        p('<b>8. TOMONLARNING HUQUQIY MANZILLARI</b>', sBs),
        sp(2),
        sign_table,
        sp(3),
        qr_table,
    ]

    doc.build(story)
    return buf.getvalue()