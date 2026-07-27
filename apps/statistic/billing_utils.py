# apps/statistic/billing_utils.py
"""Billing ma'lumotlarini batch usulda olish uchun yordamchi."""

from django.db.models import Sum

STATUS_DISPLAY = {
    'unpaid':    "To'lanmagan",
    'partial':   "Qisman to'langan",
    'paid':      "To'liq to'langan",
    'cancelled': "Bekor qilingan",
    'none':      "To'lanmagan",   # invoice yo'q = to'lanmagan
}

# openpyxl PatternFill uchun fgColor kodlari
STATUS_COLOR = {
    'paid':      'C6EFCE',  # yashil
    'partial':   'FFEB9C',  # sariq
    'unpaid':    'FFC7CE',  # qizil/pushti
    'cancelled': 'D9D9D9',  # kulrang
    'none':      'F2F3F4',  # och kulrang
}


METHOD_DISPLAY = {
    'cash':          'Naqd',
    'card':          'Plastik karta',
    'bank_transfer': "Bank o'tkazmasi",
    'insurance':     "Sug'urta",
}


def build_payment_lookup(patient_ids):
    """
    Bemorlar to'lov ma'lumotlarini batch usulda oladi (5 ta DB so'rov).

    Qaytaradi: {
        patient_id: {
            'status':      str,      # To'liq to'langan / Qisman / ...
            'status_code': str,      # paid / partial / unpaid / none
            'paid':        float,    # to'langan summa (refundlar ayirilgan)
            'discount':    float,    # chegirma summasi
            'methods':     str,      # "Naqd", "Plastik karta, Naqd", ...
        }
    }
    """
    from apps.billing.models import Invoice, Payment, Refund, Discount

    patient_ids = list(patient_ids)
    if not patient_ids:
        return {}

    inv_map = {
        inv.patient_card_id: inv.status
        for inv in Invoice.objects.filter(
            patient_card_id__in=patient_ids
        ).only('patient_card_id', 'status')
    }

    paid_map = dict(
        Payment.objects.filter(invoice__patient_card_id__in=patient_ids)
        .values('invoice__patient_card_id')
        .annotate(t=Sum('amount'))
        .values_list('invoice__patient_card_id', 't')
    )

    refund_map = dict(
        Refund.objects.filter(invoice__patient_card_id__in=patient_ids)
        .values('invoice__patient_card_id')
        .annotate(t=Sum('amount'))
        .values_list('invoice__patient_card_id', 't')
    )

    discount_map = dict(
        Discount.objects.filter(invoice__patient_card_id__in=patient_ids)
        .values('invoice__patient_card_id')
        .annotate(t=Sum('amount'))
        .values_list('invoice__patient_card_id', 't')
    )

    # To'lov usullari: {patient_id: ['Naqd', 'Karta', ...]}
    methods_raw = (
        Payment.objects.filter(invoice__patient_card_id__in=patient_ids)
        .values('invoice__patient_card_id', 'method')
        .distinct()
    )
    methods_map: dict[int, list] = {}
    for row in methods_raw:
        pid = row['invoice__patient_card_id']
        label = METHOD_DISPLAY.get(row['method'], row['method'])
        methods_map.setdefault(pid, [])
        if label not in methods_map[pid]:
            methods_map[pid].append(label)

    result = {}
    for pid in patient_ids:
        sc = inv_map.get(pid, 'none')
        paid = float(paid_map.get(pid, 0) or 0) - float(refund_map.get(pid, 0) or 0)
        result[pid] = {
            'status':      STATUS_DISPLAY.get(sc, sc),
            'status_code': sc,
            'paid':        max(0.0, paid),
            'discount':    float(discount_map.get(pid, 0) or 0),
            'methods':     ', '.join(methods_map.get(pid, [])),
        }
    return result


def payment_summary_from_lookup(pay_lookup):
    """
    pay_lookup dict dan umumiy statistika hisoblaydi.

    Qaytaradi:
        {
            'paid': N, 'partial': N, 'unpaid': N, 'none': N,
            'total_paid': float,
            'total_discount': float,
            'by_method': {'Naqd': float, 'Plastik karta': float, ...}
        }
    """
    counts = {'paid': 0, 'partial': 0, 'unpaid': 0, 'cancelled': 0, 'none': 0}
    total_paid = 0.0
    total_discount = 0.0
    by_method: dict[str, float] = {}

    for info in pay_lookup.values():
        sc = info['status_code']
        counts[sc] = counts.get(sc, 0) + 1
        total_paid    += info['paid']
        total_discount += info.get('discount', 0.0)
        for m in info.get('methods', '').split(', '):
            if m:
                by_method[m] = by_method.get(m, 0.0) + info['paid']

    counts['total_paid']     = total_paid
    counts['total_discount'] = total_discount
    counts['by_method']      = by_method
    return counts
