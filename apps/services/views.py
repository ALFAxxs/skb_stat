# apps/services/views.py

import io
import json
from datetime import date, timedelta

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Sum, Q, ExpressionWrapper, DecimalField, F
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone

from apps.users.decorators import role_required
from apps.patients.models import PatientCard, Doctor
from .models import ServiceCategory, Service, PatientService
from .forms import PatientServiceForm, ServiceResultForm


# ==================== AJAX ====================

@login_required
def service_search(request):
    """AJAX — xizmat qidirish"""
    q = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    patient_id = request.GET.get('patient_id', '')

    qs = Service.objects.filter(is_active=True).select_related('category').order_by('name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if category_id:
        qs = qs.filter(category_id=category_id)
    # Bo'sh qidiruv — faqat 20 ta ko'rsatish
    # Kategoriya tanlangan bo'lsa — hammasi
    limit = 50 if category_id else 20

    # Bemor kategoriyasiga qarab narx hisoblash
    patient_category = 'railway'
    if patient_id:
        try:
            patient = PatientCard.objects.get(pk=patient_id)
            patient_category = patient.patient_category or 'railway'
        except PatientCard.DoesNotExist:
            pass

    data = []
    for s in qs[:limit]:
        price = s.price_for_patient(patient_category)
        data.append({
            'id': s.id,
            'name': str(s),
            'category': s.category.name,
            'category_id': s.category_id,
            'price': float(price),
            'price_normal': float(s.price_normal),
            'price_railway': float(s.price_railway),
        })

    return JsonResponse(data, safe=False)


# ==================== BEMOR XIZMATLARI ====================

@login_required
def patient_services(request, patient_pk):
    """Bemorning barcha xizmatlari"""
    patient = get_object_or_404(PatientCard, pk=patient_pk)

    services = PatientService.objects.filter(
        patient_card=patient
    ).select_related(
        'service__category', 'ordered_by', 'performed_by'
    ).order_by('-ordered_at')

    categories = ServiceCategory.objects.filter(is_active=True)

    # Moliyaviy umumlama
    from django.db.models import ExpressionWrapper, DecimalField, F as F_
    _pxq0 = ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())
    totals = services.annotate(_pxq=_pxq0).aggregate(
        total_sum=Sum('_pxq'),
        count=Sum('quantity'),
    )
    total_price = (totals['total_sum'] or 0)

    # Kategoriya bo'yicha umumlama
    from django.db.models import ExpressionWrapper, DecimalField, F as F_
    cat_stats = services.values(
        'service__category__name',
        'service__category__icon',
    ).annotate(
        count=Sum('quantity'),
        total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
    ).order_by('-total')

    # Barcha aktiv shifokorlar (bo'lim bo'yicha guruhlab)
    doctors = Doctor.objects.filter(
        is_active=True
    ).select_related('department').order_by('department__name', '-is_head', 'full_name')

    from .models import PatientMedicine
    medicines = PatientMedicine.objects.filter(
        patient_card=patient
    ).select_related('medicine', 'ordered_by').order_by('-ordered_at')
    medicines_total = sum(m.total_price for m in medicines)

    return render(request, 'services/patient_services.html', {
        'patient': patient,
        'services': services,
        'categories': categories,
        'total_price': total_price,
        'total_count': totals['count'] or 0,
        'cat_stats': cat_stats,
        'doctors': doctors,
        'medicines': medicines,
        'medicines_total': medicines_total,
    })


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def add_service(request, patient_pk):
    """Bemorga xizmat qo'shish — AJAX"""
    patient = get_object_or_404(PatientCard, pk=patient_pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_id = data.get('service_id')
            quantity = int(data.get('quantity', 1))
            ordered_by_id = data.get('ordered_by_id')
            notes = data.get('notes', '')

            service = Service.objects.get(pk=service_id, is_active=True)
            price = service.price_for_patient(patient.patient_category or 'railway')

            ps = PatientService.objects.create(
                patient_card=patient,
                service=service,
                quantity=quantity,
                price=price,
                patient_category_at_order=patient.patient_category or 'railway',
                ordered_by_id=ordered_by_id if ordered_by_id else None,
                notes=notes,
            )

            return JsonResponse({
                'success': True,
                'id': ps.id,
                'service_name': service.name,
                'category': service.category.name,
                'quantity': quantity,
                'price': float(price),
                'total': float(ps.total_price),
                'status': ps.get_status_display(),
                'ordered_at': ps.ordered_at.strftime('%d.%m.%Y %H:%M'),
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'POST required'})


@login_required
@role_required('admin', 'doctor', 'statistician')
def update_service(request, pk):
    """Xizmat holatini yangilash — AJAX"""
    ps = get_object_or_404(PatientService, pk=pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            status = data.get('status')
            result = data.get('result', '')
            is_paid = data.get('is_paid', False)
            performed_by_id = data.get('performed_by_id')
            ordered_by_id = data.get('ordered_by_id')

            if status in dict(PatientService.STATUS_CHOICES):
                ps.status = status
            ps.result = result
            ps.is_paid = is_paid
            ps.performed_by_id = performed_by_id if performed_by_id else None
            if ordered_by_id is not None:
                ps.ordered_by_id = ordered_by_id if ordered_by_id else None

            if status == 'completed' and not ps.performed_at:
                ps.performed_at = timezone.now()

            ps.save()
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False})


@login_required
@role_required('admin', 'doctor', 'reception')
def delete_service(request, pk):
    """Xizmatni o'chirish"""
    ps = get_object_or_404(PatientService, pk=pk)
    patient_pk = ps.patient_card.pk

    if request.method == 'POST':
        if ps.status == 'ordered':
            ps.delete()
            return JsonResponse({'success': True})
        return JsonResponse({
            'success': False,
            'error': "Bajarilgan xizmatni o'chirib bo'lmaydi"
        })

    return JsonResponse({'success': False})


# ==================== STATISTIKA ====================

@login_required
@role_required('admin', 'statistician')
def service_statistics(request):
    """Xizmatlar statistikasi dashboard"""
    # Filterlar
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    category_id = request.GET.get('category', '')
    period = request.GET.get('period', 'month')  # day/month/year
    patient_cat = request.GET.get('patient_category', '')

    qs = PatientService.objects.exclude(status='cancelled').select_related(
        'service__category', 'patient_card'
    )

    if date_from:
        qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(ordered_at__date__lte=date_to)
    if category_id:
        qs = qs.filter(service__category_id=category_id)
    if patient_cat:
        qs = qs.filter(patient_category_at_order=patient_cat)

    # Umumiy ko'rsatkichlar
    totals = qs.aggregate(
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        count=Sum('quantity'),
        railway_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(patient_category_at_order='railway')),
        nonresident_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(
            patient_category_at_order='non_resident'
        )),
    )

    # Kategoriya bo'yicha
    from django.db.models import ExpressionWrapper, DecimalField, F as F_
    cat_stats = qs.values(
        'service__category__name',
        'service__category__icon',
        'service__category__id',
    ).annotate(
        count=Sum('quantity'),
        total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
    ).order_by('-total')

    # Eng ko'p ishlatiladigan xizmatlar (Top 10)
    from django.db.models import ExpressionWrapper, DecimalField, F as F_
    top_services = qs.values(
        'service__name',
        'service__category__name',
    ).annotate(
        count=Sum('quantity'),
        total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
    ).order_by('-count')[:10]

    # Vaqt bo'yicha dinamika
    if period == 'day':
        time_stats = qs.annotate(
            period=TruncDay('ordered_at')
        ).values('period').annotate(
            count=Sum('quantity'),
            total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
        ).order_by('period')
    elif period == 'year':
        time_stats = qs.annotate(
            period=TruncYear('ordered_at')
        ).values('period').annotate(
            count=Sum('quantity'),
            total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
        ).order_by('period')
    else:
        time_stats = qs.annotate(
            period=TruncMonth('ordered_at')
        ).values('period').annotate(
            count=Sum('quantity'),
            total=Sum(ExpressionWrapper(F_('price') * F_('quantity'), output_field=DecimalField())),
        ).order_by('period')

    time_labels = [
        item['period'].strftime('%Y-%m-%d' if period == 'day' else '%Y-%m' if period == 'month' else '%Y')
        for item in time_stats if item['period']
    ]
    time_counts = [item['count'] for item in time_stats if item['period']]
    time_totals = [float(item['total'] or 0) for item in time_stats if item['period']]

    categories = ServiceCategory.objects.filter(is_active=True)

    return render(request, 'services/statistics.html', {
        'totals': totals,
        'cat_stats': cat_stats,
        'top_services': top_services,
        'time_labels': json.dumps(time_labels),
        'time_counts': json.dumps(time_counts),
        'time_totals': json.dumps(time_totals),
        'cat_labels': json.dumps([c['service__category__name'] for c in cat_stats]),
        'cat_values': json.dumps([float(c['total'] or 0) for c in cat_stats]),
        'categories': categories,
        'date_from': date_from,
        'date_to': date_to,
        'selected_category': category_id,
        'selected_period': period,
        'selected_patient_cat': patient_cat,
        'current_filters': request.GET.urlencode(),
    })


# ==================== EXPORT ====================

@login_required
@role_required('admin', 'statistician')
def export_services_excel(request):
    """Xizmatlar hisobotini Excel ga export"""
    qs = PatientService.objects.exclude(status='cancelled').select_related(
        'service__category', 'patient_card', 'ordered_by', 'performed_by'
    )

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    category_id = request.GET.get('category')
    patient_cat = request.GET.get('patient_category')

    if date_from:
        qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(ordered_at__date__lte=date_to)
    if category_id:
        qs = qs.filter(service__category_id=category_id)
    if patient_cat:
        qs = qs.filter(patient_category_at_order=patient_cat)

    wb = openpyxl.Workbook()

    header_font = Font(bold=True, color='FFFFFF', size=10)
    header_fill = PatternFill('solid', fgColor='1F4E79')
    center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    # ===== 1-sahifa: Xizmatlar ro'yxati =====
    ws = wb.active
    ws.title = "Xizmatlar ro'yxati"

    headers = [
        '№', 'Sana', 'Bemor', 'Bemor kategoriyasi',
        'Kategoriya', 'Xizmat', 'Miqdori',
        'Narx', 'Jami', 'Holat', "To'langan",
        'Buyurtma bergan', 'Bajargan', 'Natija'
    ]
    ws.row_dimensions[1].height = 35
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    cat_display = {
        'railway': "Temir yo'lchi", 'paid': 'Pullik',
        'non_resident': 'Norezident', 'foreign': 'Chet el',
    }

    for i, ps in enumerate(qs.order_by('-ordered_at'), 1):
        row_data = [
            i,
            ps.ordered_at.strftime('%d.%m.%Y %H:%M'),
            ps.patient_card.full_name,
            cat_display.get(ps.patient_category_at_order, ps.patient_category_at_order),
            ps.service.category.name,
            ps.service.name,
            ps.quantity,
            float(ps.price),
            float(ps.total_price),
            ps.get_status_display(),
            'Ha' if ps.is_paid else "Yo'q",
            str(ps.ordered_by) if ps.ordered_by else '—',
            str(ps.performed_by) if ps.performed_by else '—',
            ps.result or '—',
        ]
        for col, val in enumerate(row_data, 1):
            cell = ws.cell(row=i + 1, column=col, value=val)
            cell.alignment = Alignment(vertical='center', wrap_text=True)
            cell.border = border
            if col == 11:
                cell.fill = PatternFill('solid', fgColor='C6EFCE' if ps.is_paid else 'FFC7CE')

    col_widths = [4, 16, 25, 16, 18, 30, 8, 12, 12, 14, 10, 22, 22, 30]
    for i, w in enumerate(col_widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # ===== 2-sahifa: Kategoriya statistikasi =====
    ws2 = wb.create_sheet("Kategoriyalar")
    ws2['A1'] = "Xizmat kategoriyalari bo'yicha statistika"
    ws2['A1'].font = Font(bold=True, size=13, color='1F4E79')

    h2 = ['Kategoriya', 'Xizmatlar soni', "Jami summa (so'm)", "To'langan (so'm)"]
    for col, h in enumerate(h2, 1):
        cell = ws2.cell(row=3, column=col, value=h)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center
        cell.border = border

    from django.db.models import ExpressionWrapper, DecimalField, F
    _pxq_cat = ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())
    cat_data = qs.annotate(_pxq=_pxq_cat).values('service__category__name').annotate(
        count=Sum('quantity'),
        total=Sum('_pxq'),
    ).order_by('-total')

    for i, row in enumerate(cat_data, 4):
        ws2.cell(row=i, column=1, value=row['service__category__name']).border = border
        ws2.cell(row=i, column=2, value=row['count']).border = border
        ws2.cell(row=i, column=3, value=float(row['total'] or 0)).border = border

    for col, w in enumerate([25, 15, 20, 20], 1):
        ws2.column_dimensions[get_column_letter(col)].width = w

    # ===== 3-sahifa: Umumiy hisobot =====
    ws3 = wb.create_sheet("Umumiy hisobot")
    ws3['A1'] = "Umumiy moliyaviy hisobot"
    ws3['A1'].font = Font(bold=True, size=13, color='1F4E79')

    totals_agg = qs.aggregate(
        total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        count=Sum('quantity'),
        railway=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(patient_category_at_order='railway')),
        nonresident=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(
            patient_category_at_order='non_resident'
        )),
    )
    summary = [
        ('Jami xizmatlar soni', totals_agg['count'] or 0),
        ("Jami summa (so'm)", float(totals_agg['total'] or 0)),
        ("Temir yo'lchilar daromadi (so'm)", float(totals_agg['railway'] or 0)),
        ("Norezidentlar daromadi (so'm)", float(totals_agg['nonresident'] or 0)),
    ]
    for i, (label, val) in enumerate(summary, 3):
        ws3.cell(row=i, column=1, value=label).font = Font(bold=True)
        ws3.cell(row=i, column=2, value=val)

    ws3.column_dimensions['A'].width = 35
    ws3.column_dimensions['B'].width = 20

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="xizmatlar_hisoboti.xlsx"'
    wb.save(response)
    return response


@login_required
@role_required('admin', 'statistician')
def export_services_pdf(request):
    """Xizmatlar hisobotini PDF ga export"""
    qs = PatientService.objects.exclude(status='cancelled').select_related(
        'service__category', 'patient_card'
    ).order_by('-ordered_at')

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(ordered_at__date__lte=date_to)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4),
        rightMargin=1*cm, leftMargin=1*cm,
        topMargin=1.5*cm, bottomMargin=1*cm
    )
    styles = getSampleStyleSheet()
    small = ParagraphStyle('sm', parent=styles['Normal'], fontSize=7, leading=9)
    title_style = ParagraphStyle(
        'title', parent=styles['Heading1'],
        fontSize=14, alignment=1, spaceAfter=10
    )

    elements = [
        Paragraph("Xizmatlar hisoboti", title_style),
        Spacer(1, 0.3*cm)
    ]

    headers = [
        '№', 'Sana', 'Bemor', 'Kategoriya',
        'Xizmat', 'Miqdor', 'Narx', 'Jami', "To'langan"
    ]
    table_data = [[Paragraph(h, small) for h in headers]]

    for i, ps in enumerate(qs, 1):
        table_data.append([
            str(i),
            ps.ordered_at.strftime('%d.%m.%Y'),
            Paragraph(ps.patient_card.full_name, small),
            Paragraph(ps.service.category.name, small),
            Paragraph(ps.service.name, small),
            str(ps.quantity),
            f"{float(ps.price):,.0f}",
            f"{float(ps.total_price):,.0f}",
            'Ha' if ps.is_paid else "Yo'q",
        ])

    col_widths = [
        1*cm, 2.5*cm, 4*cm, 3*cm,
        5*cm, 1.5*cm, 2.5*cm, 2.5*cm, 2*cm
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="xizmatlar_hisoboti.pdf"'
    return response

# ==================== DORI-DARMON ====================

@login_required
def medicine_search(request):
    """AJAX — dori qidirish"""
    from .models import Medicine
    q = request.GET.get('q', '').strip()
    qs = Medicine.objects.filter(is_active=True)
    if q:
        qs = qs.filter(name__icontains=q)
    qs = qs[:30]
    data = [{'id': m.id, 'name': m.name, 'unit': m.unit} for m in qs]
    return JsonResponse(data, safe=False)


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def add_medicine(request, patient_pk):
    """Bemorga dori qo'shish — AJAX POST"""
    from .models import Medicine, PatientMedicine
    patient = get_object_or_404(PatientCard, pk=patient_pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            medicine_id  = data.get('medicine_id')
            quantity     = data.get('quantity', 1)
            price        = data.get('price', 0)
            ordered_by_id = data.get('ordered_by_id')
            notes        = data.get('notes', '')

            from decimal import Decimal
            medicine = Medicine.objects.get(pk=medicine_id, is_active=True)
            pm = PatientMedicine.objects.create(
                patient_card  = patient,
                medicine      = medicine,
                quantity      = Decimal(str(quantity)),
                price         = Decimal(str(price)),
                ordered_by_id = ordered_by_id or None,
                notes         = notes,
            )
            return JsonResponse({
                'success': True,
                'id': pm.id,
                'medicine_name': medicine.name,
                'unit': medicine.unit,
                'quantity': str(pm.quantity),
                'price': str(pm.price),
                'total': str(pm.total_price),
                'ordered_by': pm.ordered_by.full_name if pm.ordered_by else '—',
                'ordered_at': pm.ordered_at.strftime('%d.%m.%Y %H:%M'),
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False})


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def update_medicine(request, pk):
    """Dori yangilash — AJAX POST"""
    from .models import PatientMedicine
    from decimal import Decimal
    pm = get_object_or_404(PatientMedicine, pk=pk)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pm.quantity      = Decimal(str(data.get('quantity', pm.quantity)))
            pm.price         = Decimal(str(data.get('price', pm.price)))
            pm.ordered_by_id = data.get('ordered_by_id') or None
            pm.notes         = data.get('notes', pm.notes)
            pm.save()
            return JsonResponse({
                'success': True,
                'total': str(pm.total_price),
                'ordered_by': pm.ordered_by.full_name if pm.ordered_by else '—',
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False})


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def delete_medicine(request, pk):
    """Dori o'chirish — AJAX DELETE"""
    from .models import PatientMedicine
    pm = get_object_or_404(PatientMedicine, pk=pk)
    if request.method == 'POST':
        pm.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


# ==================== DORI STATISTIKASI ====================

@login_required
def medicine_statistics(request):
    """Dori-darmonlar statistikasi"""
    from .models import Medicine, PatientMedicine
    from django.db.models import Sum, Count, Q
    from django.db.models.functions import TruncMonth, TruncDay, TruncYear

    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    medicine_id = request.GET.get('medicine', '')
    period      = request.GET.get('period', 'month')

    qs = PatientMedicine.objects.select_related(
        'medicine', 'patient_card', 'ordered_by'
    )

    if date_from:
        qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(ordered_at__date__lte=date_to)
    if medicine_id:
        qs = qs.filter(medicine_id=medicine_id)

    # Umumiy ko'rsatkichlar
    totals = qs.aggregate(
        total_records=Sum('quantity'),
        total_qty=Sum('quantity'),
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        patients=Count('patient_card', distinct=True),
    )

    # Eng ko'p ishlatiladigan dorilar TOP-20
    top_medicines = (
        qs.values('medicine__name', 'medicine__unit', 'medicine_id')
        .annotate(
            rec_count=Sum('quantity'),
            total_qty=Sum('quantity'),
            total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            patient_count=Count('patient_card', distinct=True),
        )
        .order_by('-total_sum')[:20]
    )

    # Dinamika (trend)
    if period == 'day':
        trunc_fn = TruncDay
        fmt = '%d.%m.%Y'
    elif period == 'year':
        trunc_fn = TruncYear
        fmt = '%Y'
    else:
        trunc_fn = TruncMonth
        fmt = '%Y-%m'

    trend = (
        qs.annotate(period=trunc_fn('ordered_at'))
        .values('period')
        .annotate(total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())), qty=Sum('quantity'), cnt=Sum('quantity'))
        .order_by('period')
    )
    trend_labels = [t['period'].strftime(fmt) for t in trend if t['period']]
    trend_values = [float(t['total'] or 0) for t in trend if t['period']]

    # Dorilar ro'yxati (filter uchun)
    medicines_list = Medicine.objects.filter(is_active=True).order_by('name')

    current_filters = request.GET.urlencode()

    import json
    return render(request, 'services/medicine_statistics.html', {
        'totals': totals,
        'top_medicines': top_medicines,
        'trend_labels': json.dumps(trend_labels),
        'trend_values': json.dumps(trend_values),
        'medicines_list': medicines_list,
        'date_from': date_from,
        'date_to': date_to,
        'selected_medicine': medicine_id,
        'selected_period': period,
        'current_filters': current_filters,
    })


@login_required
def export_medicine_excel(request):
    """Dori statistikasi Excel"""
    from .models import PatientMedicine
    from django.db.models import Sum, Count
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    medicine_id = request.GET.get('medicine', '')

    qs = PatientMedicine.objects.select_related('medicine', 'patient_card', 'ordered_by')
    if date_from: qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:   qs = qs.filter(ordered_at__date__lte=date_to)
    if medicine_id: qs = qs.filter(medicine_id=medicine_id)

    GOLD  = PatternFill('solid', fgColor='856404')
    LGOLD = PatternFill('solid', fgColor='FFF8E1')
    WHITE = PatternFill('solid', fgColor='FFFFFF')
    WFONT = Font(color='FFFFFF', bold=True, size=10)
    BOLD  = Font(bold=True, size=10)
    NORM  = Font(size=10)
    CENTER = Alignment(horizontal='center', vertical='center')
    LEFT   = Alignment(horizontal='left',   vertical='center')
    RIGHT  = Alignment(horizontal='right',  vertical='center')
    brd = Side(style='thin', color='CCCCCC')
    BRD = Border(left=brd, right=brd, top=brd, bottom=brd)

    wb = openpyxl.Workbook()

    # Sheet 1 - Umumiy hisobot
    ws1 = wb.active
    ws1.title = "Hisobot"
    ws1.column_dimensions['A'].width = 5
    ws1.column_dimensions['B'].width = 35
    ws1.column_dimensions['C'].width = 12
    ws1.column_dimensions['D'].width = 14
    ws1.column_dimensions['E'].width = 14
    ws1.column_dimensions['F'].width = 18

    ws1.merge_cells('A1:F1')
    c = ws1.cell(row=1, column=1, value="DORI-DARMONLAR STATISTIKASI")
    c.fill = GOLD; c.font = Font(color='FFFFFF', bold=True, size=13)
    c.alignment = CENTER
    ws1.row_dimensions[1].height = 30

    if date_from or date_to:
        ws1.merge_cells('A2:F2')
        c = ws1.cell(row=2, column=1,
            value=f"Davr: {date_from or '—'} dan {date_to or '—'} gacha")
        c.font = BOLD; c.alignment = CENTER
        ws1.row_dimensions[2].height = 18

    heads = ['№', 'Dori nomi', 'Birlik', 'Jami miqdor', 'Bemorlar', "Jami summa (so'm)"]
    for col, h in enumerate(heads, 1):
        c = ws1.cell(row=3, column=col, value=h)
        c.fill = GOLD; c.font = WFONT; c.alignment = CENTER; c.border = BRD
    ws1.row_dimensions[3].height = 22

    top = (
        qs.values('medicine__name', 'medicine__unit')
        .annotate(tq=Sum('quantity'), tp=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())), pc=Count('patient_card', distinct=True))
        .order_by('-tp')
    )

    grand = 0
    for ri, row in enumerate(top, 1):
        tp = float(row['tp'] or 0)
        grand += tp
        data = [ri, row['medicine__name'], row['medicine__unit'],
                float(row['tq'] or 0), row['pc'], tp]
        for col, val in enumerate(data, 1):
            c = ws1.cell(row=ri+3, column=col, value=val)
            c.font = NORM
            c.alignment = CENTER if col in (1,3,4,5) else (RIGHT if col==6 else LEFT)
            c.border = BRD
            if col == 6: c.number_format = '#,##0'
            c.fill = LGOLD if ri % 2 == 0 else WHITE
        ws1.row_dimensions[ri+3].height = 18

    last = len(list(top)) + 4
    ws1.merge_cells(start_row=last, start_column=1, end_row=last, end_column=5)
    c = ws1.cell(row=last, column=1, value="JAMI:")
    c.fill = GOLD; c.font = WFONT; c.alignment = LEFT; c.border = BRD
    c6 = ws1.cell(row=last, column=6, value=grand)
    c6.fill = GOLD; c6.font = WFONT; c6.alignment = RIGHT
    c6.border = BRD; c6.number_format = '#,##0'
    ws1.row_dimensions[last].height = 24

    # Sheet 2 - Batafsil ro'yxat
    ws2 = wb.create_sheet("Batafsil")
    ws2.column_dimensions['A'].width = 5
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 30
    ws2.column_dimensions['D'].width = 12
    ws2.column_dimensions['E'].width = 14
    ws2.column_dimensions['F'].width = 14
    ws2.column_dimensions['G'].width = 20
    ws2.column_dimensions['H'].width = 20

    ws2.merge_cells('A1:H1')
    c = ws2.cell(row=1, column=1, value="BATAFSIL RO'YXAT")
    c.fill = GOLD; c.font = Font(color='FFFFFF', bold=True, size=12)
    c.alignment = CENTER
    ws2.row_dimensions[1].height = 26

    heads2 = ['№', 'Bemor', 'Dori nomi', 'Birlik', 'Miqdori', "Narxi", "Jami", 'Sana']
    for col, h in enumerate(heads2, 1):
        c = ws2.cell(row=2, column=col, value=h)
        c.fill = GOLD; c.font = WFONT; c.alignment = CENTER; c.border = BRD
    ws2.row_dimensions[2].height = 22

    for ri, pm in enumerate(qs.order_by('-ordered_at'), 1):
        data = [
            ri,
            pm.patient_card.full_name,
            pm.medicine.name,
            pm.medicine.unit,
            float(pm.quantity),
            float(pm.price),
            float(pm.total_price),
            pm.ordered_at.strftime('%d.%m.%Y'),
        ]
        for col, val in enumerate(data, 1):
            c = ws2.cell(row=ri+2, column=col, value=val)
            c.font = NORM; c.border = BRD
            c.alignment = CENTER if col in (1,4,5,8) else (RIGHT if col in (6,7) else LEFT)
            if col in (6,7): c.number_format = '#,##0'
            c.fill = LGOLD if ri % 2 == 0 else WHITE
        ws2.row_dimensions[ri+2].height = 17

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="dori_statistika.xlsx"'
    wb.save(response)
    return response


# ==================== OPERATSIYA STATISTIKASI ====================

@login_required
def operation_statistics(request):
    """Operatsiya turlari bo'yicha statistika"""
    from apps.patients.models import SurgicalOperation, OperationType
    from django.db.models import Count, Q
    import json

    date_from    = request.GET.get('date_from', '')
    date_to      = request.GET.get('date_to', '')
    op_type_id   = request.GET.get('op_type', '')
    anesthesia   = request.GET.get('anesthesia', '')

    qs = SurgicalOperation.objects.select_related(
        'operation_type', 'patient_card'
    ).filter(operation_type__isnull=False)

    if date_from:
        qs = qs.filter(operation_date__gte=date_from)
    if date_to:
        qs = qs.filter(operation_date__lte=date_to)
    if op_type_id:
        qs = qs.filter(operation_type_id=op_type_id)
    if anesthesia:
        qs = qs.filter(anesthesia=anesthesia)

    # Har bir operatsiya turi bo'yicha statistika
    op_stats = (
        qs.values(
            'operation_type__id',
            'operation_type__code',
            'operation_type__name',
        )
        .annotate(
            total_count=Count('id'),
            # Bemor kategoriyasi bo'yicha
            railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            # Narkoz bo'yicha
            anesthesia_yes=Count('id', filter=Q(anesthesia='yes')),
            anesthesia_no=Count('id', filter=Q(anesthesia='no')),
            anesthesia_local=Count('id', filter=Q(anesthesia='local')),
        )
        .order_by('-total_count')
    )

    # Xizmat narxlari bilan bog'lash (agar Service da OperationType bog'liq bo'lsa)
    # SurgicalOperation da narx yo'q - faqat PatientService orqali olish mumkin
    # Shu sababli PatientService orqali operatsiya xizmatlarini topamiz
    from apps.services.models import PatientService
    from django.db.models import Sum

    # Operatsiya xizmatlari summasi (service kategoriyasi 'surgery' bo'lganlar)
    svc_totals_by_cat = {}
    surgery_svcs = (
        PatientService.objects
        .filter(service__category__category_type='surgery')
        .values('patient_card__patient_category')
        .annotate(total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())), cnt=Sum('quantity'))
    )
    for s in surgery_svcs:
        cat = s['patient_card__patient_category']
        svc_totals_by_cat[cat] = {
            'total': float(s['total'] or 0),
            'count': s['cnt']
        }

    # Umumiy ko'rsatkichlar
    totals = qs.aggregate(
        total=Count('id'),
        railway=Count('id', filter=Q(patient_card__patient_category='railway')),
        paid=Count('id', filter=Q(patient_card__patient_category='paid')),
        nonresident=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        with_anesthesia=Count('id', filter=Q(anesthesia='yes')),
        local_anesthesia=Count('id', filter=Q(anesthesia='local')),
        no_anesthesia=Count('id', filter=Q(anesthesia='no')),
    )

    # Trend (oylik)
    from django.db.models.functions import TruncMonth
    trend = (
        qs.annotate(month=TruncMonth('operation_date'))
        .values('month')
        .annotate(cnt=Count('id'))
        .order_by('month')
    )
    trend_labels = [t['month'].strftime('%Y-%m') for t in trend if t['month']]
    trend_values = [t['cnt'] for t in trend if t['month']]

    op_types_list = OperationType.objects.filter(is_active=True).order_by('name')
    current_filters = request.GET.urlencode()

    return render(request, 'services/operation_statistics.html', {
        'op_stats': op_stats,
        'totals': totals,
        'svc_totals_by_cat': svc_totals_by_cat,
        'trend_labels': json.dumps(trend_labels),
        'trend_values': json.dumps(trend_values),
        'op_types_list': op_types_list,
        'date_from': date_from,
        'date_to': date_to,
        'selected_op_type': op_type_id,
        'selected_anesthesia': anesthesia,
        'current_filters': current_filters,
    })


@login_required
def export_operation_excel(request):
    """Operatsiya statistikasi Excel export"""
    from apps.patients.models import SurgicalOperation
    from django.db.models import Count, Sum, Q, ExpressionWrapper, DecimalField, F
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    date_from  = request.GET.get('date_from', '')
    date_to    = request.GET.get('date_to', '')
    op_type_id = request.GET.get('op_type', '')
    anesthesia = request.GET.get('anesthesia', '')

    qs = SurgicalOperation.objects.select_related(
        'operation_type', 'patient_card'
    ).filter(operation_type__isnull=False)

    if date_from:    qs = qs.filter(operation_date__gte=date_from)
    if date_to:      qs = qs.filter(operation_date__lte=date_to)
    if op_type_id:   qs = qs.filter(operation_type_id=op_type_id)
    if anesthesia:   qs = qs.filter(anesthesia=anesthesia)

    # Stillar
    BLUE  = PatternFill('solid', fgColor='1F4E79')
    LBLUE = PatternFill('solid', fgColor='D6E4F0')
    GREEN = PatternFill('solid', fgColor='E9F7EF')
    YELL  = PatternFill('solid', fgColor='FFF3CD')
    RED   = PatternFill('solid', fgColor='FDEDEC')
    WHITE = PatternFill('solid', fgColor='FFFFFF')
    TOTAL = PatternFill('solid', fgColor='145A32')

    WF   = Font(color='FFFFFF', bold=True, size=10)
    BOLD = Font(bold=True, size=10)
    NORM = Font(size=9)
    C    = Alignment(horizontal='center', vertical='center', wrap_text=True)
    L    = Alignment(horizontal='left',   vertical='center', wrap_text=True)
    R    = Alignment(horizontal='right',  vertical='center')
    brd  = Side(style='thin', color='CCCCCC')
    BRD  = Border(left=brd, right=brd, top=brd, bottom=brd)

    wb = openpyxl.Workbook()

    # ===== SHEET 1: OPERATSIYA TURI BO'YICHA =====
    ws1 = wb.active
    ws1.title = "Operatsiya turlari"

    col_w = [5, 12, 35, 12, 12, 14, 16, 14, 14, 12, 12]
    for ci, w in enumerate(col_w, 1):
        from openpyxl.utils import get_column_letter
        ws1.column_dimensions[get_column_letter(ci)].width = w

    ws1.merge_cells('A1:K1')
    c = ws1.cell(row=1, column=1, value="OPERATSIYA TURLARI BO'YICHA STATISTIKA")
    c.fill = BLUE; c.font = Font(color='FFFFFF', bold=True, size=13)
    c.alignment = C
    ws1.row_dimensions[1].height = 30

    if date_from or date_to:
        ws1.merge_cells('A2:K2')
        c = ws1.cell(row=2, column=1,
            value=f"Davr: {date_from or '—'} dan {date_to or '—'} gacha")
        c.font = BOLD; c.alignment = C
        ws1.row_dimensions[2].height = 18
        hdr_row = 3
    else:
        hdr_row = 2

    headers = [
        '№', 'Kod', 'Operatsiya nomi',
        'Jami\nsoni',
        "Temir\nyo'lchi",
        'Pullik',
        'Norezident',
        "Narkoz\nbilan",
        'Mahalliy\nnarkoz',
        'Narkozsiz',
        'Asorat\nbor',
    ]
    for col, h in enumerate(headers, 1):
        c = ws1.cell(row=hdr_row, column=col, value=h)
        c.fill = BLUE; c.font = WF; c.alignment = C; c.border = BRD
    ws1.row_dimensions[hdr_row].height = 36

    op_stats = (
        qs.values(
            'operation_type__id',
            'operation_type__code',
            'operation_type__name',
        )
        .annotate(
            total_count=Count('id'),
            railway=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            anes_yes=Count('id', filter=Q(anesthesia='yes')),
            anes_local=Count('id', filter=Q(anesthesia='local')),
            anes_no=Count('id', filter=Q(anesthesia='no')),
            has_complication=Count('id', filter=~Q(complication='') & Q(complication__isnull=False)),
        )
        .order_by('-total_count')
    )

    totals_row = [0] * 9
    dr = hdr_row + 1
    for ri, op in enumerate(op_stats, 1):
        vals = [
            ri,
            op['operation_type__code'] or '—',
            op['operation_type__name'],
            op['total_count'],
            op['railway'],
            op['paid'],
            op['nonresident'],
            op['anes_yes'],
            op['anes_local'],
            op['anes_no'],
            op['has_complication'],
        ]
        for j in range(3, 11): totals_row[j-3] += vals[j] if j < len(vals) else 0
        for col, val in enumerate(vals, 1):
            c = ws1.cell(row=dr, column=col, value=val)
            c.font = NORM; c.border = BRD
            c.alignment = C if col != 3 else L
            fill = [LBLUE, YELL, WHITE, RED][ri % 4] if col > 3 else WHITE
            if ri % 2 == 0: c.fill = PatternFill('solid', fgColor='F0F6FC')
        ws1.row_dimensions[dr].height = 18
        dr += 1

    # Jami
    tot_vals = ['', '', 'JAMI:'] + [qs.aggregate(t=Count('id'))['t']] + [
        qs.filter(patient_card__patient_category='railway').count(),
        qs.filter(patient_card__patient_category='paid').count(),
        qs.filter(patient_card__patient_category='non_resident').count(),
        qs.filter(anesthesia='yes').count(),
        qs.filter(anesthesia='local').count(),
        qs.filter(anesthesia='no').count(),
        qs.exclude(complication='').exclude(complication__isnull=True).count(),
    ]
    for col, val in enumerate(tot_vals, 1):
        c = ws1.cell(row=dr, column=col, value=val)
        c.fill = BLUE; c.font = WF; c.alignment = C if col != 3 else L; c.border = BRD
    ws1.row_dimensions[dr].height = 22

    # ===== SHEET 2: BATAFSIL RO'YXAT =====
    ws2 = wb.create_sheet("Batafsil ro'yxat")
    h2_widths = [5, 14, 28, 14, 35, 20, 16, 14, 30]
    for ci, w in enumerate(h2_widths, 1):
        from openpyxl.utils import get_column_letter
        ws2.column_dimensions[get_column_letter(ci)].width = w

    ws2.merge_cells('A1:I1')
    c = ws2.cell(row=1, column=1, value="OPERATSIYALAR BATAFSIL RO'YXATI")
    c.fill = BLUE; c.font = Font(color='FFFFFF', bold=True, size=12); c.alignment = C
    ws2.row_dimensions[1].height = 26

    h2 = ['№', 'Sana', 'Bemor', 'Bayonnoma', 'Operatsiya turi', 'Bemor turi', 'Narkoz', "Asorat bor?", 'Asorat tavsifi']
    for col, h in enumerate(h2, 1):
        c = ws2.cell(row=2, column=col, value=h)
        c.fill = BLUE; c.font = WF; c.alignment = C; c.border = BRD
    ws2.row_dimensions[2].height = 22

    for ri, op in enumerate(qs.order_by('-operation_date'), 1):
        cat_display = {
            'railway': "Temir yo'lchi",
            'paid': 'Pullik',
            'non_resident': 'Norezident',
        }.get(op.patient_card.patient_category, '—')

        has_comp = bool(op.complication and op.complication.strip())
        data = [
            ri,
            op.operation_date.strftime('%d.%m.%Y') if op.operation_date else '—',
            op.patient_card.full_name,
            op.patient_card.medical_record_number,
            str(op.operation_type) if op.operation_type else op.operation_name or '—',
            cat_display,
            op.get_anesthesia_display() if op.anesthesia else '—',
            'Ha' if has_comp else "Yo'q",
            op.complication or '—',
        ]
        for col, val in enumerate(data, 1):
            c = ws2.cell(row=ri+2, column=col, value=val)
            c.font = NORM; c.border = BRD
            c.alignment = C if col in (1,2,4,6,7,8) else L
            if ri % 2 == 0: c.fill = PatternFill('solid', fgColor='F0F6FC')
            if col == 8 and has_comp: c.fill = PatternFill('solid', fgColor='FDEDEC')
        ws2.row_dimensions[ri+2].height = 17

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="operatsiya_statistika.xlsx"'
    wb.save(response)
    return response


# ==================== XIZMAT OPERATSIYALARI STATISTIKASI ====================

@login_required
def operation_service_statistics(request):
    """is_operation=True bo'lgan xizmatlar bo'yicha statistika"""
    from django.db.models import Sum, Count, Q
    from django.db.models.functions import TruncMonth
    import json

    date_from    = request.GET.get('date_from', '')
    date_to      = request.GET.get('date_to', '')
    category_id  = request.GET.get('category', '')
    service_id   = request.GET.get('service', '')
    patient_cat  = request.GET.get('patient_category', '')

    # Faqat is_operation=True xizmatlar
    qs = PatientService.objects.filter(
        service__is_operation=True
    ).select_related('service__category', 'patient_card')

    if date_from:    qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:      qs = qs.filter(ordered_at__date__lte=date_to)
    if category_id:  qs = qs.filter(service__category_id=category_id)
    if service_id:   qs = qs.filter(service_id=service_id)
    if patient_cat:  qs = qs.filter(patient_card__patient_category=patient_cat)

    # Umumiy ko'rsatkichlar
    totals = qs.aggregate(
        total_count=Sum('quantity'),
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        patients=Count('patient_card', distinct=True),
        railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
        paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
        nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        railway_sum=Sum('price', filter=Q(patient_card__patient_category='railway')),
        paid_sum=Sum('price', filter=Q(patient_card__patient_category='paid')),
        nonresident_sum=Sum('price', filter=Q(patient_card__patient_category='non_resident')),
    )

    # Har bir operatsiya xizmati bo'yicha batafsil
    op_stats = (
        qs.values(
            'service__id',
            'service__name',
            'service__code',
            'service__category__name',
            'service__category__icon',
        )
        .annotate(
            total_count=Sum('quantity'),
            total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            patients=Count('patient_card', distinct=True),
            railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            railway_sum=Sum('price', filter=Q(patient_card__patient_category='railway')),
            paid_sum=Sum('price', filter=Q(patient_card__patient_category='paid')),
            nonresident_sum=Sum('price', filter=Q(patient_card__patient_category='non_resident')),
        )
        .order_by('-total_count')
    )

    # Kategoriya bo'yicha guruhlash
    cat_stats = (
        qs.values('service__category__name', 'service__category__icon')
        .annotate(
            count=Count('id'),
            total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            railway=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        )
        .order_by('-total')
    )

    # Oylik trend
    trend = (
        qs.annotate(month=TruncMonth('ordered_at'))
        .values('month')
        .annotate(cnt=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())))
        .order_by('month')
    )
    trend_labels = [t['month'].strftime('%Y-%m') for t in trend if t['month']]
    trend_counts = [t['cnt'] for t in trend if t['month']]
    trend_sums   = [float(t['total'] or 0) for t in trend if t['month']]

    # Filter uchun ro'yxatlar
    from .models import ServiceCategory
    op_categories = ServiceCategory.objects.filter(
        services__is_operation=True, is_active=True
    ).distinct().order_by('name')

    op_services = Service.objects.filter(
        is_operation=True, is_active=True
    ).order_by('category__name', 'name')

    current_filters = request.GET.urlencode()

    return render(request, 'services/operation_service_statistics.html', {
        'totals': totals,
        'op_stats': op_stats,
        'cat_stats': cat_stats,
        'trend_labels': json.dumps(trend_labels),
        'trend_counts': json.dumps(trend_counts),
        'trend_sums':   json.dumps(trend_sums),
        'op_categories': op_categories,
        'op_services': op_services,
        'date_from': date_from,
        'date_to': date_to,
        'selected_category': category_id,
        'selected_service': service_id,
        'selected_patient_cat': patient_cat,
        'current_filters': current_filters,
    })


@login_required
def export_operation_service_excel(request):
    """Operatsiya xizmatlari statistikasi Excel"""
    from django.db.models import Sum, Count, Q
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    category_id = request.GET.get('category', '')
    service_id  = request.GET.get('service', '')
    patient_cat = request.GET.get('patient_category', '')

    qs = PatientService.objects.filter(
        service__is_operation=True
    ).select_related('service__category', 'patient_card')
    if date_from:   qs = qs.filter(ordered_at__date__gte=date_from)
    if date_to:     qs = qs.filter(ordered_at__date__lte=date_to)
    if category_id: qs = qs.filter(service__category_id=category_id)
    if service_id:  qs = qs.filter(service_id=service_id)
    if patient_cat: qs = qs.filter(patient_card__patient_category=patient_cat)

    # Stillar
    BLUE  = PatternFill('solid', fgColor='1F4E79')
    LBLUE = PatternFill('solid', fgColor='D6E4F0')
    GREEN = PatternFill('solid', fgColor='E9F7EF')
    YELL  = PatternFill('solid', fgColor='FFF3CD')
    RED   = PatternFill('solid', fgColor='FDEDEC')
    TOTAL = PatternFill('solid', fgColor='145A32')
    WHITE = PatternFill('solid', fgColor='FFFFFF')
    WF    = Font(color='FFFFFF', bold=True, size=10)
    BOLD  = Font(bold=True, size=10)
    NORM  = Font(size=9)
    C = Alignment(horizontal='center', vertical='center', wrap_text=True)
    L = Alignment(horizontal='left',   vertical='center', wrap_text=True)
    R = Alignment(horizontal='right',  vertical='center')
    brd = Side(style='thin', color='CCCCCC')
    BRD = Border(left=brd, right=brd, top=brd, bottom=brd)

    wb = openpyxl.Workbook()

    # ===== SHEET 1: OPERATSIYA XIZMATLARI =====
    ws1 = wb.active
    ws1.title = "Operatsiya xizmatlari"

    col_widths = [5, 12, 35, 18, 10, 10, 10, 10, 14, 14, 14, 16]
    for ci, w in enumerate(col_widths, 1):
        ws1.column_dimensions[get_column_letter(ci)].width = w

    ws1.merge_cells('A1:L1')
    c = ws1.cell(row=1, column=1,
        value="OPERATSIYA XIZMATLARI BO'YICHA STATISTIKA")
    c.fill = BLUE; c.font = Font(color='FFFFFF', bold=True, size=13)
    c.alignment = C
    ws1.row_dimensions[1].height = 30

    if date_from or date_to:
        ws1.merge_cells('A2:L2')
        ws1.cell(row=2, column=1,
            value=f"Davr: {date_from or '—'} dan {date_to or '—'} gacha").font = BOLD
        ws1.row_dimensions[2].height = 18
        hdr = 3
    else:
        hdr = 2

    headers = [
        '№', 'Kod', 'Operatsiya nomi', 'Kategoriya',
        'Jami\nsoni', 'Bemorlar',
        "TY\nsoni", "Pullik\nsoni", "Nores.\nsoni",
        "TY\nsumma", "Pullik\nsumma", "Nores.\nsumma",
    ]
    for col, h in enumerate(headers, 1):
        c = ws1.cell(row=hdr, column=col, value=h)
        c.fill = BLUE; c.font = WF; c.alignment = C; c.border = BRD
    ws1.row_dimensions[hdr].height = 36

    op_stats = (
        qs.values(
            'service__code', 'service__name', 'service__category__name'
        )
        .annotate(
            tc=Count('id'),
            pts=Count('patient_card', distinct=True),
            rc=Count('id', filter=Q(patient_card__patient_category='railway')),
            pc=Count('id', filter=Q(patient_card__patient_category='paid')),
            nc=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            rs=Sum('price', filter=Q(patient_card__patient_category='railway')),
            ps=Sum('price', filter=Q(patient_card__patient_category='paid')),
            ns=Sum('price', filter=Q(patient_card__patient_category='non_resident')),
        )
        .order_by('service__category__name', '-tc')
    )

    dr = hdr + 1
    grand = {'tc':0,'pts':0,'rc':0,'pc':0,'nc':0,'rs':0,'ps':0,'ns':0}

    for ri, op in enumerate(op_stats, 1):
        vals = [
            ri,
            op['service__code'] or '—',
            op['service__name'],
            op['service__category__name'],
            op['tc'], op['pts'],
            op['rc'], op['pc'], op['nc'],
            float(op['rs'] or 0), float(op['ps'] or 0), float(op['ns'] or 0),
        ]
        for k in ('tc','pts','rc','pc','nc'):
            grand[k] += op[k] or 0
        for k, col in (('rs',10),('ps',11),('ns',12)):
            grand[k] += float(op[k] or 0)

        fill = LBLUE if ri % 2 == 0 else WHITE
        for col, val in enumerate(vals, 1):
            c = ws1.cell(row=dr, column=col, value=val)
            c.font = NORM; c.border = BRD; c.fill = fill
            c.alignment = C if col in (1,5,6,7,8,9) else (R if col > 9 else L)
            if col > 9: c.number_format = '#,##0'
        ws1.row_dimensions[dr].height = 18
        dr += 1

    # Jami qatori
    tot = ['', '', 'JAMI:', '',
           grand['tc'], grand['pts'],
           grand['rc'], grand['pc'], grand['nc'],
           grand['rs'], grand['ps'], grand['ns']]
    for col, val in enumerate(tot, 1):
        c = ws1.cell(row=dr, column=col, value=val)
        c.fill = BLUE; c.font = WF; c.border = BRD
        c.alignment = C if col in (1,5,6,7,8,9) else (R if col > 9 else L)
        if col > 9: c.number_format = '#,##0'
    ws1.row_dimensions[dr].height = 24

    # Umumiy summa qatori
    dr += 1
    total_sum = grand['rs'] + grand['ps'] + grand['ns']
    ws1.merge_cells(start_row=dr, start_column=1, end_row=dr, end_column=9)
    c = ws1.cell(row=dr, column=1, value="UMUMIY DAROMAD:")
    c.fill = TOTAL; c.font = WF; c.alignment = L; c.border = BRD
    c2 = ws1.cell(row=dr, column=10, value=total_sum)
    c2.fill = TOTAL; c2.font = Font(color='FFFFFF', bold=True, size=12)
    c2.number_format = '#,##0'; c2.alignment = R; c2.border = BRD
    ws1.merge_cells(start_row=dr, start_column=10, end_row=dr, end_column=12)
    ws1.row_dimensions[dr].height = 26

    # ===== SHEET 2: KATEGORIYA BO'YICHA =====
    ws2 = wb.create_sheet("Kategoriya bo'yicha")
    for ci, w in enumerate([5, 25, 10, 12, 14, 14, 14, 16], 1):
        ws2.column_dimensions[get_column_letter(ci)].width = w

    ws2.merge_cells('A1:H1')
    c = ws2.cell(row=1, column=1, value="KATEGORIYA BO'YICHA")
    c.fill = BLUE; c.font = Font(color='FFFFFF', bold=True, size=12); c.alignment = C
    ws2.row_dimensions[1].height = 26

    h2 = ['№', 'Kategoriya', 'Jami soni', 'Bemorlar',
          "TY soni", "Pullik soni", "Nores. soni", "Jami summa"]
    for col, h in enumerate(h2, 1):
        c = ws2.cell(row=2, column=col, value=h)
        c.fill = BLUE; c.font = WF; c.alignment = C; c.border = BRD
    ws2.row_dimensions[2].height = 24

    cat_stats = (
        qs.values('service__category__name', 'service__category__icon')
        .annotate(
            cnt=Count('id'), pts=Count('patient_card', distinct=True),
            rc=Count('id', filter=Q(patient_card__patient_category='railway')),
            pc=Count('id', filter=Q(patient_card__patient_category='paid')),
            nc=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        )
        .order_by('-total')
    )

    cat_grand = 0
    for ri, cat in enumerate(cat_stats, 1):
        icon = cat['service__category__icon'] or ''
        name = f"{icon} {cat['service__category__name']}"
        vals = [ri, name, cat['cnt'], cat['pts'],
                cat['rc'], cat['pc'], cat['nc'],
                float(cat['total'] or 0)]
        cat_grand += float(cat['total'] or 0)
        fill = LBLUE if ri % 2 == 0 else WHITE
        for col, val in enumerate(vals, 1):
            c = ws2.cell(row=ri+2, column=col, value=val)
            c.font = NORM; c.border = BRD; c.fill = fill
            c.alignment = C if col in (1,3,4,5,6,7) else (R if col == 8 else L)
            if col == 8: c.number_format = '#,##0'
        ws2.row_dimensions[ri+2].height = 20

    last2 = cat_stats.count() + 3
    ws2.merge_cells(start_row=last2, start_column=1, end_row=last2, end_column=7)
    c = ws2.cell(row=last2, column=1, value="JAMI:")
    c.fill = BLUE; c.font = WF; c.alignment = L; c.border = BRD
    c8 = ws2.cell(row=last2, column=8, value=cat_grand)
    c8.fill = BLUE; c8.font = WF; c8.number_format = '#,##0'
    c8.alignment = R; c8.border = BRD
    ws2.row_dimensions[last2].height = 22

    # ===== SHEET 3: BATAFSIL =====
    ws3 = wb.create_sheet("Batafsil")
    for ci, w in enumerate([5, 14, 28, 28, 16, 14, 14], 1):
        ws3.column_dimensions[get_column_letter(ci)].width = w

    ws3.merge_cells('A1:G1')
    c = ws3.cell(row=1, column=1, value="BATAFSIL RO'YXAT")
    c.fill = BLUE; c.font = Font(color='FFFFFF', bold=True, size=12); c.alignment = C
    ws3.row_dimensions[1].height = 26

    h3 = ['№', 'Sana', 'Bemor', 'Operatsiya nomi', 'Bemor turi', "Narx (so'm)", "Jami (so'm)"]
    for col, h in enumerate(h3, 1):
        c = ws3.cell(row=2, column=col, value=h)
        c.fill = BLUE; c.font = WF; c.alignment = C; c.border = BRD
    ws3.row_dimensions[2].height = 22

    CAT_MAP = {'railway': "Temir yo'lchi", 'paid': 'Pullik', 'non_resident': 'Norezident'}
    for ri, ps in enumerate(qs.order_by('-ordered_at'), 1):
        data = [
            ri,
            ps.ordered_at.strftime('%d.%m.%Y'),
            ps.patient_card.full_name,
            ps.service.name,
            CAT_MAP.get(ps.patient_card.patient_category, '—'),
            float(ps.price),
            float(ps.total_price),
        ]
        fill = LBLUE if ri % 2 == 0 else WHITE
        for col, val in enumerate(data, 1):
            c = ws3.cell(row=ri+2, column=col, value=val)
            c.font = NORM; c.border = BRD; c.fill = fill
            c.alignment = C if col in (1,2,5) else (R if col > 5 else L)
            if col > 5: c.number_format = '#,##0'
        ws3.row_dimensions[ri+2].height = 17

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="operatsiya_xizmatlari.xlsx"'
    wb.save(response)
    return response


# ==================== BIRLASHTIRILGAN STATISTIKA ====================

@login_required
def statistics_combined(request):
    """Barcha statistikalarni bitta sahifada — tab bilan"""
    import json
    from django.db.models import Sum, Count, Q
    from django.db.models.functions import TruncMonth, TruncDay, TruncYear
    from .models import PatientMedicine, Medicine, ServiceCategory

    active_tab = request.GET.get('tab', 'services')

    # --- UMUMIY FILTERLAR ---
    date_from   = request.GET.get('date_from', '')
    date_to     = request.GET.get('date_to', '')
    patient_cat = request.GET.get('patient_category', '')
    period      = request.GET.get('period', 'month')

    # ==================== 1. XIZMATLAR ====================
    svc_qs = PatientService.objects.exclude(
        status='cancelled'
    ).select_related('service__category', 'patient_card')
    if date_from:    svc_qs = svc_qs.filter(ordered_at__date__gte=date_from)
    if date_to:      svc_qs = svc_qs.filter(ordered_at__date__lte=date_to)
    if patient_cat:  svc_qs = svc_qs.filter(patient_category_at_order=patient_cat)
    if request.GET.get('svc_category'):
        svc_qs = svc_qs.filter(service__category_id=request.GET['svc_category'])

    svc_totals = svc_qs.aggregate(
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        count=Sum('quantity'),
        railway_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(patient_category_at_order='railway')),
        paid_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(patient_category_at_order='paid')),
        nonresident_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()), filter=Q(patient_category_at_order='non_resident')),
        railway_count=Sum('quantity', filter=Q(patient_category_at_order='railway')),
        paid_count=Sum('quantity', filter=Q(patient_category_at_order='paid')),
        nonresident_count=Sum('quantity', filter=Q(patient_category_at_order='non_resident')),
    )
    svc_cat_stats = svc_qs.values(
        'service__category__name', 'service__category__icon', 'service__category__id'
    ).annotate(count=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()))).order_by('-total')

    top_services = svc_qs.values(
        'service__name', 'service__category__name'
    ).annotate(count=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField()))).order_by('-count')[:15]

    if period == 'day':
        from django.db.models.functions import TruncDay
        trunc_fn = TruncDay
        fmt = '%d.%m.%Y'
    elif period == 'year':
        from django.db.models.functions import TruncYear
        trunc_fn = TruncYear
        fmt = '%Y'
    else:
        trunc_fn = TruncMonth
        fmt = '%Y-%m'

    svc_trend = (
        svc_qs.annotate(p=trunc_fn('ordered_at'))
        .values('p').annotate(cnt=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())))
        .order_by('p')
    )
    svc_trend_labels = [t['p'].strftime(fmt) for t in svc_trend if t['p']]
    svc_trend_values = [float(t['total'] or 0) for t in svc_trend if t['p']]

    # ==================== 2. DORILAR ====================
    med_qs = PatientMedicine.objects.select_related('medicine', 'patient_card')
    if date_from:   med_qs = med_qs.filter(ordered_at__date__gte=date_from)
    if date_to:     med_qs = med_qs.filter(ordered_at__date__lte=date_to)
    if patient_cat: med_qs = med_qs.filter(patient_card__patient_category=patient_cat)
    if request.GET.get('medicine'):
        med_qs = med_qs.filter(medicine_id=request.GET['medicine'])

    med_totals = med_qs.aggregate(
        total_records=Sum('quantity'),
        total_qty=Sum('quantity'),
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        patients=Count('patient_card', distinct=True),
    )
    top_medicines = (
        med_qs.values('medicine__name', 'medicine__unit')
        .annotate(
            rec_count=Sum('quantity'),
            total_qty=Sum('quantity'),
            total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            patient_count=Count('patient_card', distinct=True),
        ).order_by('-total_sum')[:15]
    )
    med_trend = (
        med_qs.annotate(p=TruncMonth('ordered_at'))
        .values('p').annotate(total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())), qty=Sum('quantity'))
        .order_by('p')
    )
    med_trend_labels = [t['p'].strftime('%Y-%m') for t in med_trend if t['p']]
    med_trend_values = [float(t['total'] or 0) for t in med_trend if t['p']]

    # ==================== 3. OPERATSIYA (SurgicalOperation) ====================
    from apps.patients.models import SurgicalOperation, OperationType
    op_qs = SurgicalOperation.objects.filter(
        operation_type__isnull=False
    ).select_related('operation_type', 'patient_card')
    if date_from:   op_qs = op_qs.filter(operation_date__gte=date_from)
    if date_to:     op_qs = op_qs.filter(operation_date__lte=date_to)
    if patient_cat: op_qs = op_qs.filter(patient_card__patient_category=patient_cat)
    if request.GET.get('op_type'):
        op_qs = op_qs.filter(operation_type_id=request.GET['op_type'])

    op_totals = op_qs.aggregate(
        total=Count('id'),
        railway=Count('id', filter=Q(patient_card__patient_category='railway')),
        paid=Count('id', filter=Q(patient_card__patient_category='paid')),
        nonresident=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        with_anesthesia=Count('id', filter=Q(anesthesia='yes')),
        local_anesthesia=Count('id', filter=Q(anesthesia='local')),
        no_anesthesia=Count('id', filter=Q(anesthesia='no')),
    )
    op_stats = (
        op_qs.values('operation_type__id', 'operation_type__code', 'operation_type__name')
        .annotate(
            total_count=Count('id'),
            railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            anesthesia_yes=Count('id', filter=Q(anesthesia='yes')),
            anesthesia_local=Count('id', filter=Q(anesthesia='local')),
            anesthesia_no=Count('id', filter=Q(anesthesia='no')),
        ).order_by('-total_count')
    )
    op_trend = (
        op_qs.annotate(p=TruncMonth('operation_date'))
        .values('p').annotate(cnt=Count('id'))
        .order_by('p')
    )
    op_trend_labels = [t['p'].strftime('%Y-%m') for t in op_trend if t['p']]
    op_trend_values = [t['cnt'] for t in op_trend if t['p']]

    # ==================== 4. OPERATSIYA XIZMATLARI ====================
    opx_qs = PatientService.objects.filter(
        service__is_operation=True
    ).select_related('service__category', 'patient_card')
    if date_from:   opx_qs = opx_qs.filter(ordered_at__date__gte=date_from)
    if date_to:     opx_qs = opx_qs.filter(ordered_at__date__lte=date_to)
    if patient_cat: opx_qs = opx_qs.filter(patient_card__patient_category=patient_cat)
    if request.GET.get('opx_category'):
        opx_qs = opx_qs.filter(service__category_id=request.GET['opx_category'])

    opx_totals = opx_qs.aggregate(
        total_count=Sum('quantity'),
        total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
        patients=Count('patient_card', distinct=True),
        railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
        paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
        nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        railway_sum=Sum('price', filter=Q(patient_card__patient_category='railway')),
        paid_sum=Sum('price', filter=Q(patient_card__patient_category='paid')),
        nonresident_sum=Sum('price', filter=Q(patient_card__patient_category='non_resident')),
    )
    opx_stats = (
        opx_qs.values(
            'service__id', 'service__name', 'service__code',
            'service__category__name', 'service__category__icon',
        ).annotate(
            total_count=Sum('quantity'),
            total_sum=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            patients=Count('patient_card', distinct=True),
            railway_count=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid_count=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident_count=Count('id', filter=Q(patient_card__patient_category='non_resident')),
            railway_sum=Sum('price', filter=Q(patient_card__patient_category='railway')),
            paid_sum=Sum('price', filter=Q(patient_card__patient_category='paid')),
            nonresident_sum=Sum('price', filter=Q(patient_card__patient_category='non_resident')),
        ).order_by('-total_count')
    )
    opx_cat_stats = (
        opx_qs.values('service__category__name', 'service__category__icon')
        .annotate(count=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())),
            railway=Count('id', filter=Q(patient_card__patient_category='railway')),
            paid=Count('id', filter=Q(patient_card__patient_category='paid')),
            nonresident=Count('id', filter=Q(patient_card__patient_category='non_resident')),
        ).order_by('-total')
    )
    opx_trend = (
        opx_qs.annotate(p=TruncMonth('ordered_at'))
        .values('p').annotate(cnt=Sum('quantity'), total=Sum(ExpressionWrapper(F('price') * F('quantity'), output_field=DecimalField())))
        .order_by('p')
    )
    opx_trend_labels = [t['p'].strftime('%Y-%m') for t in opx_trend if t['p']]
    opx_trend_counts = [t['cnt'] for t in opx_trend if t['p']]
    opx_trend_sums   = [float(t['total'] or 0) for t in opx_trend if t['p']]

    # Filter ro'yxatlar
    categories       = ServiceCategory.objects.filter(is_active=True)
    op_categories    = ServiceCategory.objects.filter(services__is_operation=True, is_active=True).distinct()
    medicines_list   = Medicine.objects.filter(is_active=True).order_by('name')
    op_types_list    = OperationType.objects.filter(is_active=True).order_by('name')

    current_filters = request.GET.urlencode()

    return render(request, 'services/statistics_combined.html', {
        'active_tab': active_tab,
        'date_from': date_from,
        'date_to': date_to,
        'patient_cat': patient_cat,
        'period': period,
        'current_filters': current_filters,

        # Xizmatlar
        'svc_totals': svc_totals,
        'svc_cat_stats': svc_cat_stats,
        'top_services': top_services,
        'svc_trend_labels': json.dumps(svc_trend_labels),
        'svc_trend_values': json.dumps(svc_trend_values),
        'categories': categories,
        'selected_svc_category': request.GET.get('svc_category', ''),
        'selected_period': period,

        # Dorilar
        'med_totals': med_totals,
        'top_medicines': top_medicines,
        'med_trend_labels': json.dumps(med_trend_labels),
        'med_trend_values': json.dumps(med_trend_values),
        'medicines_list': medicines_list,
        'selected_medicine': request.GET.get('medicine', ''),

        # Operatsiyalar (SurgicalOperation)
        'op_totals': op_totals,
        'op_stats': op_stats,
        'op_trend_labels': json.dumps(op_trend_labels),
        'op_trend_values': json.dumps(op_trend_values),
        'op_types_list': op_types_list,
        'selected_op_type': request.GET.get('op_type', ''),

        # Operatsiya xizmatlari
        'opx_totals': opx_totals,
        'opx_stats': opx_stats,
        'opx_cat_stats': opx_cat_stats,
        'opx_trend_labels': json.dumps(opx_trend_labels),
        'opx_trend_counts': json.dumps(opx_trend_counts),
        'opx_trend_sums':   json.dumps(opx_trend_sums),
        'op_categories': op_categories,
        'selected_opx_category': request.GET.get('opx_category', ''),
        'selected_patient_cat': patient_cat,
    })


# ==================== OPERATSIYALARNI BELGILASH ====================

@login_required
@role_required('admin', 'statistician')
def mark_operations(request):
    """Xizmatlarni operatsiya deb belgilash sahifasi"""
    from .models import ServiceCategory

    if request.method == 'POST':
        action     = request.POST.get('action')
        service_ids = request.POST.getlist('service_ids')
        if service_ids:
            is_op = (action == 'mark')
            updated = Service.objects.filter(pk__in=service_ids).update(is_operation=is_op)
            if is_op:
                messages.success(request, f"✅ {updated} ta xizmat operatsiya deb belgilandi.")
            else:
                messages.warning(request, f"❌ {updated} ta xizmatdan operatsiya belgisi olib tashlandi.")
        else:
            messages.error(request, "Hech bir xizmat tanlanmadi.")
        return redirect('mark_operations')

    # Kategoriyalar va ularning xizmatlari
    categories_raw = ServiceCategory.objects.filter(is_active=True).order_by('name')
    categories = []
    total_services = 0
    total_operations = 0

    for cat in categories_raw:
        svcs = list(
            Service.objects.filter(category=cat, is_active=True).order_by('name')
        )
        if not svcs:
            continue
        op_count  = sum(1 for s in svcs if s.is_operation)
        cat.services_list = svcs
        cat.total_count   = len(svcs)
        cat.op_count      = op_count
        categories.append(cat)
        total_services   += len(svcs)
        total_operations += op_count

    return render(request, 'services/mark_operations.html', {
        'categories':       categories,
        'total_services':   total_services,
        'total_operations': total_operations,
    })