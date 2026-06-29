# apps/billing/pdf_utils.py
"""WeasyPrint ishlamasa (masalan GTK kutubxonalari yo'q Windows muhitda) ishlatiladigan ReportLab fallback."""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_invoice_pdf_bytes(ctx, patient) -> bytes:
    invoice = ctx['invoice']
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=14*mm, bottomMargin=14*mm)
    W = A4[0] - 30*mm

    sTitle = ParagraphStyle('title', fontName='Helvetica-Bold', fontSize=14, textColor=colors.HexColor('#1F4E79'))
    sSub = ParagraphStyle('sub', fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#555'))
    sSec = ParagraphStyle('sec', fontName='Helvetica-Bold', fontSize=10.5, textColor=colors.HexColor('#1F4E79'), spaceBefore=10, spaceAfter=4)
    sCell = ParagraphStyle('cell', fontName='Helvetica', fontSize=8.5)
    sCellB = ParagraphStyle('cellB', fontName='Helvetica-Bold', fontSize=8.5)

    def hr():
        return HRFlowable(width="100%", thickness=1, color=colors.HexColor('#1F4E79'))

    def fmt(n):
        try:
            return f"{int(round(float(n))):,}".replace(',', ' ')
        except (TypeError, ValueError):
            return str(n)

    story = [
        Paragraph(f"Hisob-faktura № {invoice.invoice_number}", sTitle),
        Paragraph(f"Sana: {invoice.created_at.strftime('%d.%m.%Y')} &nbsp;|&nbsp; Holati: {invoice.get_status_display()}", sSub),
        Spacer(1, 4), hr(), Spacer(1, 6),
        Paragraph(
            f"<b>Bemor:</b> {patient.full_name} &nbsp;|&nbsp; "
            f"<b>Tug'ilgan sana:</b> {patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else '-'} &nbsp;|&nbsp; "
            f"<b>Toifa:</b> {patient.get_patient_category_display()}", sSub),
        Paragraph(
            f"<b>Bayonnoma №:</b> {patient.medical_record_number}"
            + (f" / {patient.case_sheet_number}" if patient.case_sheet_number else '')
            + f" &nbsp;|&nbsp; <b>Bo'lim:</b> {patient.department or '-'} &nbsp;|&nbsp; "
            f"<b>Shifokor:</b> {patient.attending_doctor or '-'}", sSub),
        Spacer(1, 4),
    ]

    def section_table(headers, rows, col_widths, total_label, total_value):
        data = [[Paragraph(h, sCellB) for h in headers]]
        for r in rows:
            data.append([Paragraph(str(c), sCell) for c in r])
        data.append([Paragraph(total_label, sCellB), '', '', ''][:len(headers)-1] + [Paragraph(f"{fmt(total_value)} so'm", sCellB)])
        t = Table(data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7f8fa')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eef2f7')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dde2e8')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('SPAN', (0, -1), (-2, -1)),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        return t

    for sec in ctx['section_list']:
        if not sec['items']:
            continue
        story.append(Paragraph(sec['label'], sSec))
        rows = [[i.service.name, i.quantity, fmt(i.price), fmt(i.total_price)] for i in sec['items']]
        story.append(section_table(
            ["Nomi", "Miqdor", "Narxi", "Jami"], rows,
            [W*0.42, W*0.16, W*0.20, W*0.22],
            f"{sec['label']} jami", sec['subtotal']))

    if ctx['medicines']:
        story.append(Paragraph("Dori-darmonlar", sSec))
        rows = [[m.medicine.name, str(m.quantity), fmt(m.price), m.get_source_display(), fmt(m.total_price)] for m in ctx['medicines']]
        data = [[Paragraph(h, sCellB) for h in ["Nomi", "Miqdor", "Narxi", "Manba", "Jami"]]]
        for r in rows:
            data.append([Paragraph(str(c), sCell) for c in r])
        data.append([Paragraph("Dorilar jami", sCellB), '', '', '', Paragraph(f"{fmt(ctx['medicines_total'])} so'm", sCellB)])
        t = Table(data, colWidths=[W*0.32, W*0.14, W*0.18, W*0.18, W*0.18])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7f8fa')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#eef2f7')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dde2e8')),
            ('SPAN', (0, -1), (-2, -1)),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    if ctx['consumables']:
        story.append(Paragraph("Sarflanadigan materiallar", sSec))
        rows = [[c.consumable.name, str(c.quantity), fmt(c.price), fmt(c.total_price)] for c in ctx['consumables']]
        story.append(section_table(
            ["Nomi", "Miqdor", "Narxi", "Jami"], rows,
            [W*0.42, W*0.16, W*0.20, W*0.22],
            "Materiallar jami", ctx['consumables_total']))

    if ctx['payments']:
        story.append(Paragraph("To'lovlar tarixi", sSec))
        data = [[Paragraph(h, sCellB) for h in ["Sana", "Summa", "Usul", "Kassir"]]]
        for p in ctx['payments']:
            data.append([Paragraph(str(c), sCell) for c in [
                p.created_at.strftime('%d.%m.%Y %H:%M'), fmt(p.amount), p.get_method_display(),
                p.cashier.get_full_name() if p.cashier else '-',
            ]])
        t = Table(data, colWidths=[W*0.28, W*0.24, W*0.24, W*0.24])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f7f8fa')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#dde2e8')),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(t)

    story.append(Spacer(1, 8))
    summary_rows = [
        ["Jami summa", f"{fmt(ctx['subtotal'])} so'm"],
        ["Chegirma", f"-{fmt(ctx['discount_total'])} so'm"],
        ["Sug'urta qoplamasi", f"{fmt(ctx['insurance_coverage'])} so'm"],
        ["To'langan", f"{fmt(ctx['paid_total'])} so'm"],
        ["Qolgan qarz", f"{fmt(ctx['remaining'])} so'm"],
        ["UMUMIY JAMI", f"{fmt(ctx['grand_total'])} so'm"],
    ]
    data = [[Paragraph(r[0], sCellB if r[0] != "UMUMIY JAMI" else ParagraphStyle('g', fontName='Helvetica-Bold', fontSize=11, textColor=colors.white)),
             Paragraph(r[1], sCellB if r[0] != "UMUMIY JAMI" else ParagraphStyle('g2', fontName='Helvetica-Bold', fontSize=11, textColor=colors.white, alignment=TA_RIGHT))]
            for r in summary_rows]
    t = Table(data, colWidths=[W*0.7, W*0.3])
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -2), 0.4, colors.HexColor('#dde2e8')),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#1F4E79')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(t)

    doc.build(story)
    return buf.getvalue()
