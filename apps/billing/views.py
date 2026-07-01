# apps/billing/views.py

import json
import logging
from collections import defaultdict
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from apps.patients.models import PatientCard, PatientTransfer
from apps.services.models import PatientService, PatientMedicine
from apps.users.decorators import role_required
from .models import Invoice, Payment, Discount, Refund, Consumable, PatientConsumable, BillingAuditLog

logger = logging.getLogger(__name__)

FINANCE_ROLES = ('admin', 'statistician', 'reception')


def _bounded_decimal(value, max_digits, decimal_places):
    """Decimal'ga o'giradi va maydon max_digits/decimal_places chegarasini tekshiradi."""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    limit = Decimal(10) ** (max_digits - decimal_places)
    if abs(d) >= limit:
        return None
    return d


def _get_or_create_invoice(patient):
    invoice, created = Invoice.objects.get_or_create(
        patient_card=patient,
        defaults={'invoice_number': f"INV-{patient.pk:06d}"},
    )
    if created:
        BillingAuditLog.objects.create(
            invoice=invoice, action='invoice_created',
            description="Hisob-faktura avtomatik yaratildi",
        )
    return invoice


def _gather_billing_data(patient):
    """Hisob-faktura uchun barcha bo'limlar va summalarni yig'ish."""
    invoice = _get_or_create_invoice(patient)

    all_services = list(
        PatientService.objects.filter(patient_card=patient)
        .select_related('service__category', 'ordered_by', 'performed_by')
        .order_by('service__category__name', 'service__name')
    )

    # Narxlar ro'yxatidagi haqiqiy kategoriyalar bo'yicha guruhlash
    sections_by_cat = defaultdict(list)
    cat_objects = {}
    for s in all_services:
        cat = s.service.category if s.service_id and s.service.category_id else None
        key = cat.pk if cat else 0
        sections_by_cat[key].append(s)
        if cat:
            cat_objects[cat.pk] = cat

    # Kategoriyalarni nom bo'yicha tartiblab section_list yasash
    section_list = []
    for cat_pk, items in sorted(
        sections_by_cat.items(),
        key=lambda x: cat_objects[x[0]].name if x[0] else 'я'
    ):
        label = cat_objects[cat_pk].name if cat_pk else _("Boshqa xizmatlar")
        subtotal = sum((s.price * s.quantity for s in items), Decimal('0'))
        section_list.append({
            'key': f'cat_{cat_pk}',
            'label': label,
            'items': items,
            'subtotal': subtotal,
        })

    services_total = sum((s.price * s.quantity for s in all_services), Decimal('0'))

    medicines = list(
        PatientMedicine.objects.filter(patient_card=patient)
        .select_related('medicine', 'ordered_by').order_by('medicine__name')
    )
    medicines_total = sum((m.total_price for m in medicines), Decimal('0'))

    consumables = list(
        PatientConsumable.objects.filter(patient_card=patient)
        .select_related('consumable', 'ordered_by').order_by('-ordered_at')
    )
    consumables_total = sum((c.total_price for c in consumables), Decimal('0'))

    subtotal = services_total + medicines_total + consumables_total

    discounts = list(invoice.discounts.select_related('created_by'))
    discount_total = sum((d.amount for d in discounts), Decimal('0'))

    refunds = list(invoice.refunds.select_related('created_by'))
    refund_total = sum((r.amount for r in refunds), Decimal('0'))

    payments = list(invoice.payments.select_related('cashier'))
    paid_total = sum((p.amount for p in payments), Decimal('0')) - refund_total

    insurance_coverage = Decimal('0')  # hozircha sug'urta integratsiyasi yo'q

    grand_total = subtotal - discount_total - insurance_coverage
    if grand_total < 0:
        grand_total = Decimal('0')
    remaining = grand_total - paid_total
    if remaining < 0:
        remaining = Decimal('0')

    if paid_total <= 0:
        new_status = 'unpaid'
    elif remaining <= 0:
        new_status = 'paid'
    else:
        new_status = 'partial'
    if invoice.status != 'cancelled' and invoice.status != new_status:
        invoice.status = new_status
        invoice.save(update_fields=['status', 'updated_at'])

    # Ko'chirish tarixi
    transfers = list(
        PatientTransfer.objects.filter(patient_card=patient).select_related(
            'from_department', 'from_doctor', 'to_department', 'to_doctor',
        ).order_by('transferred_at')
    )

    audit_logs = list(invoice.audit_logs.select_related('actor')[:30])

    return {
        'invoice': invoice,
        'section_list': section_list,
        'services_total': services_total,
        'medicines': medicines,
        'medicines_total': medicines_total,
        'consumables': consumables,
        'consumables_total': consumables_total,
        'subtotal': subtotal,
        'discounts': discounts,
        'discount_total': discount_total,
        'refunds': refunds,
        'refund_total': refund_total,
        'payments': payments,
        'paid_total': paid_total,
        'insurance_coverage': insurance_coverage,
        'grand_total': grand_total,
        'remaining': remaining,
        'transfers': transfers,
        'audit_logs': audit_logs,
    }


@login_required
def invoice_detail(request, pk):
    """Hisob-faktura — ekran ko'rinishi"""
    patient = get_object_or_404(PatientCard, pk=pk)
    ctx = _gather_billing_data(patient)
    ctx['patient'] = patient
    ctx['can_manage'] = request.user.is_superuser or request.user.role in FINANCE_ROLES
    ctx['all_consumables'] = Consumable.objects.filter(is_active=True)
    return render(request, 'billing/invoice_detail.html', ctx)


@login_required
def invoice_print(request, pk):
    """Hisob-faktura — chop etish uchun standalone hujjat"""
    patient = get_object_or_404(PatientCard, pk=pk)
    ctx = _gather_billing_data(patient)
    ctx['patient'] = patient
    return render(request, 'billing/invoice_print.html', ctx)


@login_required
def invoice_pdf(request, pk):
    """Hisob-faktura — PDF yuklab olish"""
    patient = get_object_or_404(PatientCard, pk=pk)
    ctx = _gather_billing_data(patient)
    ctx['patient'] = patient
    html_str = render_to_string('billing/invoice_print.html', ctx)
    try:
        from weasyprint import HTML as WP
        pdf_bytes = WP(string=html_str).write_pdf()
    except Exception as e:
        logger.warning(f"invoice_pdf weasyprint unavailable, falling back to reportlab: {e}")
        try:
            from .pdf_utils import generate_invoice_pdf_bytes
            pdf_bytes = generate_invoice_pdf_bytes(ctx, patient)
        except Exception as e2:
            logger.error(f"invoice_pdf reportlab fallback error: {e2}", exc_info=True)
            return HttpResponse("PDF generatsiya qilishda xato yuz berdi", status=500)
    resp = HttpResponse(pdf_bytes, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{ctx["invoice"].invoice_number}.pdf"'
    return resp


@login_required
@role_required(*FINANCE_ROLES)
def record_payment(request, pk):
    """To'lovni qayd etish — AJAX POST"""
    patient = get_object_or_404(PatientCard, pk=pk)
    invoice = _get_or_create_invoice(patient)
    if request.method != 'POST':
        return JsonResponse({'success': False})
    try:
        data = json.loads(request.body)
        amount = _bounded_decimal(data.get('amount'), 12, 2)
        method = data.get('method', 'cash')
        comment = data.get('comment', '')
        if amount is None or amount <= 0:
            return JsonResponse({'success': False, 'error': _("Summani to'g'ri kiriting")})
        if method not in dict(Payment.METHOD_CHOICES):
            method = 'cash'

        payment = Payment.objects.create(
            invoice=invoice, amount=amount, method=method,
            cashier=request.user, comment=comment,
        )
        BillingAuditLog.objects.create(
            invoice=invoice, actor=request.user, action='payment_added',
            description=f"{amount} so'm ({payment.get_method_display()})",
        )
        ctx = _gather_billing_data(patient)
        return JsonResponse({
            'success': True,
            'paid_total': str(ctx['paid_total']),
            'remaining': str(ctx['remaining']),
            'status': ctx['invoice'].get_status_display(),
        })
    except Exception as e:
        logger.error(f"record_payment error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': _("To'lovni saqlashda xato yuz berdi")})


@login_required
@role_required(*FINANCE_ROLES)
def add_discount(request, pk):
    """Chegirma qo'shish — AJAX POST"""
    patient = get_object_or_404(PatientCard, pk=pk)
    invoice = _get_or_create_invoice(patient)
    if request.method != 'POST':
        return JsonResponse({'success': False})
    try:
        data = json.loads(request.body)
        amount = _bounded_decimal(data.get('amount'), 12, 2)
        reason = data.get('reason', '')
        if amount is None or amount <= 0:
            return JsonResponse({'success': False, 'error': _("Summani to'g'ri kiriting")})

        Discount.objects.create(invoice=invoice, amount=amount, reason=reason, created_by=request.user)
        BillingAuditLog.objects.create(
            invoice=invoice, actor=request.user, action='discount_added',
            description=f"{amount} so'm — {reason}" if reason else f"{amount} so'm",
        )
        ctx = _gather_billing_data(patient)
        return JsonResponse({
            'success': True,
            'discount_total': str(ctx['discount_total']),
            'grand_total': str(ctx['grand_total']),
            'remaining': str(ctx['remaining']),
        })
    except Exception as e:
        logger.error(f"add_discount error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': _("Chegirmani saqlashda xato yuz berdi")})


@login_required
@role_required(*FINANCE_ROLES)
def add_refund(request, pk):
    """Qaytarish (refund) qo'shish — AJAX POST"""
    patient = get_object_or_404(PatientCard, pk=pk)
    invoice = _get_or_create_invoice(patient)
    if request.method != 'POST':
        return JsonResponse({'success': False})
    try:
        data = json.loads(request.body)
        amount = _bounded_decimal(data.get('amount'), 12, 2)
        reason = data.get('reason', '')
        if amount is None or amount <= 0:
            return JsonResponse({'success': False, 'error': _("Summani to'g'ri kiriting")})

        Refund.objects.create(invoice=invoice, amount=amount, reason=reason, created_by=request.user)
        BillingAuditLog.objects.create(
            invoice=invoice, actor=request.user, action='refund_added',
            description=f"{amount} so'm — {reason}" if reason else f"{amount} so'm",
        )
        ctx = _gather_billing_data(patient)
        return JsonResponse({
            'success': True,
            'paid_total': str(ctx['paid_total']),
            'remaining': str(ctx['remaining']),
            'status': ctx['invoice'].get_status_display(),
        })
    except Exception as e:
        logger.error(f"add_refund error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': _("Qaytarishni saqlashda xato yuz berdi")})


@login_required
@role_required(*FINANCE_ROLES, 'doctor', 'nurse', 'head_nurse')
def add_consumable(request, pk):
    """Sarflanadigan material qo'shish — AJAX POST"""
    patient = get_object_or_404(PatientCard, pk=pk)
    if request.method != 'POST':
        return JsonResponse({'success': False})
    try:
        data = json.loads(request.body)
        consumable_id = data.get('consumable_id')
        quantity = _bounded_decimal(data.get('quantity', 1), 10, 2)
        price = _bounded_decimal(data.get('price', 0), 12, 2)
        if quantity is None:
            return JsonResponse({'success': False, 'error': _("Miqdori noto'g'ri yoki juda katta")})
        if price is None:
            return JsonResponse({'success': False, 'error': _("Narx noto'g'ri yoki juda katta (maksimal 9999999999.99 so'm)")})

        consumable = Consumable.objects.get(pk=consumable_id, is_active=True)
        pc = PatientConsumable.objects.create(
            patient_card=patient, consumable=consumable,
            quantity=quantity, price=price,
            ordered_by=request.user, notes=data.get('notes', ''),
        )
        invoice = _get_or_create_invoice(patient)
        BillingAuditLog.objects.create(
            invoice=invoice, actor=request.user, action='consumable_added',
            description=f"{consumable.name} x{quantity}",
        )
        return JsonResponse({
            'success': True,
            'id': pc.id,
            'name': consumable.name,
            'unit': consumable.unit,
            'quantity': str(pc.quantity),
            'price': str(pc.price),
            'total': str(pc.total_price),
        })
    except Consumable.DoesNotExist:
        return JsonResponse({'success': False, 'error': _('Material topilmadi')})
    except Exception as e:
        logger.error(f"add_consumable error: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': _("Material qo'shishda xato yuz berdi")})


@login_required
@role_required(*FINANCE_ROLES, 'doctor', 'nurse', 'head_nurse')
def delete_consumable(request, pk):
    """Sarflanadigan materialni o'chirish — AJAX POST"""
    pc = get_object_or_404(PatientConsumable, pk=pk)
    if request.method == 'POST':
        pc.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})


@login_required
@role_required(*FINANCE_ROLES)
def recalculate(request, pk):
    """Hisob-fakturani qayta hisoblash — AJAX POST"""
    patient = get_object_or_404(PatientCard, pk=pk)
    invoice = _get_or_create_invoice(patient)
    ctx = _gather_billing_data(patient)
    BillingAuditLog.objects.create(invoice=invoice, actor=request.user, action='recalculated')
    return JsonResponse({
        'success': True,
        'services_total': str(ctx['services_total']),
        'medicines_total': str(ctx['medicines_total']),
        'consumables_total': str(ctx['consumables_total']),
        'subtotal': str(ctx['subtotal']),
        'discount_total': str(ctx['discount_total']),
        'grand_total': str(ctx['grand_total']),
        'paid_total': str(ctx['paid_total']),
        'remaining': str(ctx['remaining']),
        'status': ctx['invoice'].get_status_display(),
    })
