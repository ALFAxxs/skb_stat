"""
LabResult uchun PDF generatsiya.
WeasyPrint ishlatiladi (pip install weasyprint).
Agar o'rnatilmagan bo'lsa — ReportLab fallback.
"""
import os
import base64
import secrets
from django.template.loader import render_to_string
from django.conf import settings


def _get_pdf_dir() -> str:
    path = os.path.join(settings.MEDIA_ROOT, 'lab_pdfs')
    os.makedirs(path, exist_ok=True)
    return path


def generate_pdf(result) -> str:
    """PDF yaratib, fayl yo'lini qaytaradi."""
    try:
        return _generate_weasyprint(result)
    except Exception:
        return _generate_reportlab(result)


def generate_pdf_bytes(result) -> bytes:
    """PDF bytes qaytaradi (HTTP response uchun). lab_print.html ishlatiladi."""
    ctx      = _build_print_context(result)
    html_str = render_to_string('laboratory/lab_print.html', ctx)
    try:
        from weasyprint import HTML as WP
        return WP(string=html_str).write_pdf()
    except Exception:
        return _reportlab_bytes(_build_context(result), result)


def _build_print_context(result) -> dict:
    """lab_print.html uchun context (lab_result_print view bilan bir xil)."""
    from apps.laboratory.models import LabParameter, LabResultValue
    from datetime import date

    parameters = LabParameter.objects.filter(
        template=result.template
    ).select_related('group').order_by('sort_order', 'name')

    values_map = {
        rv.parameter_id: rv
        for rv in LabResultValue.objects.filter(result=result)
    }

    params_with_values = []
    for i, param in enumerate(parameters, 1):
        rv = values_map.get(param.pk)
        params_with_values.append({
            'num':          i,
            'param':        param,
            'value':        rv.value if rv else '',
            'value_status': rv.value_status if rv else 'normal',
            'comment':      rv.comment if rv else '',
            'normal_display': param.get_normal_display(result.patient_card.gender),
        })

    patient = result.patient_card
    today   = date.today()
    age     = today.year - patient.birth_date.year - (
        (today.month, today.day) < (patient.birth_date.month, patient.birth_date.day)
    ) if patient.birth_date else '—'

    logo_b64 = ''
    for logo_path in [
        os.path.join(settings.STATIC_ROOT, 'img', 'hospital_logo.png'),
        os.path.join(settings.BASE_DIR, 'static', 'img', 'hospital_logo.png'),
    ]:
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            break

    return {
        'result':            result,
        'params_with_values': params_with_values,
        'age':               age,
        'print_date':        today,
        'logo_b64':          logo_b64,
    }


def _build_context(result) -> dict:
    from apps.laboratory.models import LabResultValue
    from datetime import date

    values = {v.parameter_id: v for v in
              LabResultValue.objects.filter(result=result).select_related('parameter__group')}
    params = result.template.parameters.select_related('group').order_by('sort_order', 'name')

    groups = {}
    ungrouped = []
    for p in params:
        rv = values.get(p.pk)
        if not rv:
            continue
        entry = {
            'param':         p,
            'value':         rv.value,
            'value_status':  rv.value_status,
            'normal_display': p.get_normal_display(result.patient_card.gender),
            'comment':       rv.comment,
        }
        if p.group_id:
            gname = p.group.name
            if gname not in groups:
                groups[gname] = []
            groups[gname].append(entry)
        else:
            ungrouped.append(entry)

    patient = result.patient_card
    today   = date.today()
    age     = today.year - patient.birth_date.year - (
        (today.month, today.day) < (patient.birth_date.month, patient.birth_date.day)
    ) if patient.birth_date else '—'

    logo_b64 = ''
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'hospital_logo.png')
    if not os.path.exists(logo_path):
        logo_path = os.path.join(settings.BASE_DIR, 'skb_stat', 'static', 'img', 'hospital_logo.png')
    if os.path.exists(logo_path):
        with open(logo_path, 'rb') as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    return {
        'result':     result,
        'patient':    patient,
        'age':        age,
        'groups':     [{'name': g, 'params': pl} for g, pl in groups.items()],
        'ungrouped':  ungrouped,
        'print_date': today,
        'qr_token':   getattr(getattr(result, 'pdf_file', None), 'secure_token', ''),
        'logo_b64':   logo_b64,
    }


def _generate_weasyprint(result) -> str:
    from weasyprint import HTML as WeasyprintHTML
    ctx      = _build_context(result)
    html_str = render_to_string('telegram_bot/lab_result_pdf.html', ctx)
    filename = f"result_{result.pk}_{secrets.token_hex(4)}.pdf"
    filepath = os.path.join(_get_pdf_dir(), filename)
    WeasyprintHTML(string=html_str).write_pdf(filepath)
    return filepath


def _generate_reportlab(result) -> str:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    ctx      = _build_context(result)
    filename = f"result_{result.pk}_{secrets.token_hex(4)}.pdf"
    filepath = os.path.join(_get_pdf_dir(), filename)

    doc    = SimpleDocTemplate(filepath, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    # Sarlavha
    story.append(Paragraph(f"<b>{result.template.name}</b>", styles['Title']))
    story.append(Spacer(1, 0.3*cm))

    patient = ctx['patient']
    story.append(Paragraph(
        f"Bemor: <b>{patient.full_name}</b> | Yosh: {ctx['age']} | "
        f"Sana: {result.created_at.strftime('%d.%m.%Y')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.5*cm))

    # Parametrlar jadvali
    STATUS_COLOR = {
        'high':     colors.HexColor('#FFF3CD'),
        'low':      colors.HexColor('#D1ECF1'),
        'critical': colors.HexColor('#F8D7DA'),
        'normal':   colors.white,
        'text':     colors.white,
    }

    all_rows = [['Parametr', 'Natija', 'Birlik', "Me'yor"]]
    row_colors = [colors.HexColor('#E3F2FD')]

    for group in ctx['groups']:
        all_rows.append([f"— {group['name']} —", '', '', ''])
        row_colors.append(colors.HexColor('#F5F5F5'))
        for e in group['params']:
            all_rows.append([
                e['param'].name,
                e['value'],
                e['param'].unit,
                e['normal_display'],
            ])
            row_colors.append(STATUS_COLOR.get(e['value_status'], colors.white))

    for e in ctx['ungrouped']:
        all_rows.append([e['param'].name, e['value'], e['param'].unit, e['normal_display']])
        row_colors.append(STATUS_COLOR.get(e['value_status'], colors.white))

    col_widths = [7*cm, 3*cm, 2.5*cm, 4*cm]
    t_style = TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID',     (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), row_colors),
    ])

    table = Table(all_rows, colWidths=col_widths, repeatRows=1)
    table.setStyle(t_style)
    story.append(table)

    if result.conclusion:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"<b>Xulosa:</b> {result.conclusion}", styles['Normal']))

    doc.build(story)
    return filepath


def _reportlab_bytes(ctx, result) -> bytes:
    """ReportLab orqali bytes qaytaradi."""
    import io
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm

    buf    = io.BytesIO()
    doc    = SimpleDocTemplate(buf, pagesize=A4,
                               leftMargin=2*cm, rightMargin=2*cm,
                               topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph(f"<b>{result.template.name}</b>", styles['Title']))
    story.append(Spacer(1, 0.3*cm))
    patient = ctx['patient']
    story.append(Paragraph(
        f"Bemor: <b>{patient.full_name}</b> | Yosh: {ctx['age']} | "
        f"Sana: {result.created_at.strftime('%d.%m.%Y')}",
        styles['Normal']
    ))
    story.append(Spacer(1, 0.5*cm))

    STATUS_COLOR = {
        'high': colors.HexColor('#FFF3CD'), 'low': colors.HexColor('#D1ECF1'),
        'critical': colors.HexColor('#F8D7DA'), 'normal': colors.white, 'text': colors.white,
    }
    all_rows   = [['Parametr', 'Natija', 'Birlik', "Me'yor"]]
    row_colors = [colors.HexColor('#E3F2FD')]

    for group in ctx['groups']:
        all_rows.append([f"— {group['name']} —", '', '', ''])
        row_colors.append(colors.HexColor('#F5F5F5'))
        for e in group['params']:
            all_rows.append([e['param'].name, e['value'], e['param'].unit, e['normal_display']])
            row_colors.append(STATUS_COLOR.get(e['value_status'], colors.white))
    for e in ctx['ungrouped']:
        all_rows.append([e['param'].name, e['value'], e['param'].unit, e['normal_display']])
        row_colors.append(STATUS_COLOR.get(e['value_status'], colors.white))

    table = Table(all_rows, colWidths=[7*cm, 3*cm, 2.5*cm, 4*cm], repeatRows=1)
    table.setStyle(TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('GRID',     (0,0), (-1,-1), 0.5, colors.grey),
        ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), row_colors),
    ]))
    story.append(table)

    if result.conclusion:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(f"<b>Xulosa:</b> {result.conclusion}", styles['Normal']))

    doc.build(story)
    return buf.getvalue()
