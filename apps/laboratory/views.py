# apps/laboratory/views.py

import base64
import json
import os
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.patients.models import PatientCard
from apps.services.models import PatientService

from .models import (
    LabOrder,
    LabOrderItem,
    LabParameter,
    LabParameterGroup,
    LabResult,
    LabResultValue,
    LabStatusLog,
    LabTemplate,
    LabTemplateService,
)


def _check_role(request):
    """Lab sahifalariga kirish huquqi: admin, doctor, laborant."""
    return request.user.is_superuser or request.user.role in ('admin', 'doctor', 'laborant')

def _can_edit_lab(request):
    """Natijani tahrirlash huquqi: faqat admin va laborant."""
    return request.user.is_superuser or request.user.role in ('admin', 'laborant')


def _item_status_priority(status):
    """Statuslar bo'yicha tartiblash uchun priority"""
    ORDER = ['sample_taken', 'in_progress', 'result_entering',
             'pending', 'completed', 'verified', 'printed', 'rejected', 'recollect']
    try:
        return ORDER.index(status)
    except ValueError:
        return 99


@login_required
def lab_home(request):
    """Bugungi lab xizmatlar, bemorlar bo'yicha guruhlangan + LabOrderItem statuslari"""
    if not _check_role(request):
        return redirect('patient_list')

    # Sana filtri
    date_str = request.GET.get('date', '')
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = date.today()
    else:
        filter_date = date.today()

    # Status filtri
    status_filter = request.GET.get('status', '')

    # Bugungi lab PatientService larni olish
    lab_ps_qs = PatientService.objects.filter(
        service__category__category_type='lab',
        ordered_at__date=filter_date,
    ).select_related(
        'patient_card', 'service', 'service__category'
    ).order_by('patient_card__full_name', '-ordered_at')

    # LabOrderItem statuslarini bir so'rovda olish
    items_map = {
        item.patient_service_id: item
        for item in LabOrderItem.objects.filter(
            patient_service__in=lab_ps_qs
        ).select_related('template', 'result')
    }

    # Bemorlar bo'yicha guruhlash
    patients_dict = {}
    for ps in lab_ps_qs:
        item = items_map.get(ps.pk)
        item_status = item.status if item else 'pending'

        # Status filtri
        if status_filter and item_status != status_filter:
            continue

        pid = ps.patient_card_id
        if pid not in patients_dict:
            patients_dict[pid] = {
                'patient':  ps.patient_card,
                'services': [],
                'statuses': [],
            }
        patients_dict[pid]['services'].append({
            'ps':         ps,
            'item':       item,
            'status':     item_status,
        })
        patients_dict[pid]['statuses'].append(item_status)

    # Tezkor statistika uchun counter
    from collections import Counter
    all_statuses = [
        s['status']
        for data in patients_dict.values()
        for s in data['services']
    ]
    status_counts = Counter(all_statuses)

    # Eng yuqori prioritetli status bo'yicha saralash
    patients_list = sorted(
        patients_dict.values(),
        key=lambda d: min(_item_status_priority(s) for s in d['statuses'])
    )

    context = {
        'patients_list':  patients_list,
        'filter_date':    filter_date,
        'today':          date.today(),
        'status_filter':  status_filter,
        'status_counts':  status_counts,
        'item_statuses':  LabOrderItem.STATUS_CHOICES,
    }
    return render(request, 'laboratory/lab_home.html', context)


def _get_or_create_order_item(patient_service, order):
    """
    PatientService uchun LabOrderItem topish yoki yaratish.
    LabTemplateService orqali shablon avtomatik biriktiriladi.
    """
    item, created = LabOrderItem.objects.get_or_create(
        patient_service=patient_service,
        defaults={'order': order},
    )
    if created or not item.order_id:
        item.order = order
        item.save(update_fields=['order'])

    # Shablon avtomatik biriktirish (agar hali yo'q bo'lsa)
    if not item.template_id:
        link = LabTemplateService.objects.filter(
            service=patient_service.service
        ).select_related('template').first()
        if link:
            item.template = link.template
            item.save(update_fields=['template'])

    return item, created


@login_required
def lab_patient(request, pk):
    """Bemorning barcha lab xizmatlari — LabOrderItem statuslari bilan"""
    if not _check_role(request):
        return redirect('patient_list')

    patient = get_object_or_404(PatientCard, pk=pk)
    can_edit = _can_edit_lab(request)

    # Bemorning barcha lab PatientService lari
    lab_services = PatientService.objects.filter(
        patient_card=patient,
        service__category__category_type='lab',
    ).select_related('service', 'service__category').order_by('-ordered_at')

    # Bemor uchun LabOrder topish yoki yaratish
    order, _ = LabOrder.objects.get_or_create(
        patient_card=patient,
        defaults={'ordered_by': request.user},
    )

    # Har bir PatientService uchun LabOrderItem topish/yaratish
    order_items = []
    for ps in lab_services:
        item, _ = _get_or_create_order_item(ps, order)
        order_items.append(item)

    # Jadval uchun order itemlarni to'ldirish
    items_with_ps = []
    for item in LabOrderItem.objects.filter(
        order=order
    ).select_related(
        'patient_service__service__category',
        'template', 'result', 'assigned_to'
    ).order_by('-patient_service__ordered_at'):
        items_with_ps.append(item)

    # Statuslar bo'yicha statistika
    from collections import Counter
    status_counts = Counter(i.status for i in items_with_ps)

    # Faol shablonlar (qo'lda biriktirish uchun)
    templates = LabTemplate.objects.filter(is_active=True).order_by('category', 'name')

    context = {
        'patient':       patient,
        'order':         order,
        'items':         items_with_ps,
        'status_counts': status_counts,
        'templates':     templates,
        'can_edit':      can_edit,
        'item_statuses': LabOrderItem.STATUS_CHOICES,
    }
    return render(request, 'laboratory/lab_patient.html', context)


@login_required
@require_POST
def lab_item_transition(request, pk):
    """
    AJAX: LabOrderItem status o'zgartirish.
    Body: {"action": "sample_taken" | "start_entry" | "reject" | "recollect" | "verify"}
    """
    if not _can_edit_lab(request):
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'}, status=403)

    item = get_object_or_404(
        LabOrderItem.objects.select_related('template', 'result', 'order'),
        pk=pk
    )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'success': False, 'error': 'JSON xatosi'}, status=400)

    action = data.get('action', '')
    note   = data.get('note', '')
    template_id = data.get('template_id')

    # Shablon biriktirish (agar action = start_entry va template_id kelsa)
    if template_id and not item.template_id:
        tmpl = LabTemplate.objects.filter(pk=template_id).first()
        if tmpl:
            item.template = tmpl
            item.save(update_fields=['template'])

    # Natija yaratish (start_entry uchun)
    if action == 'start_entry':
        if not item.template:
            return JsonResponse(
                {'success': False, 'error': 'Avval shablon tanlang'},
                status=400
            )
        # LabResult topish yoki yaratish
        if not item.result_id:
            # Bir xil template bilan mavjud result bormi?
            existing = LabResult.objects.filter(
                patient_card=item.order.patient_card,
                template=item.template,
            ).first()
            if existing:
                item.result = existing
            else:
                item.result = LabResult.objects.create(
                    patient_card=item.order.patient_card,
                    template=item.template,
                    status='draft',
                    created_by=request.user,
                )
            item.save(update_fields=['result'])
        item.transition('result_entering', request.user, note)
        return JsonResponse({
            'success':   True,
            'status':    item.status,
            'result_id': item.result_id,
            'redirect':  f'/laboratory/result/{item.result_id}/enter/',
        })

    # Oddiy status o'tishlar
    ACTION_MAP = {
        'sample_taken': 'sample_taken',
        'reject':       'rejected',
        'recollect':    'recollect',
        'verify':       'verified',
        'mark_done':    'completed',
    }
    new_status = ACTION_MAP.get(action)
    if not new_status:
        return JsonResponse({'success': False, 'error': 'Noto\'g\'ri action'}, status=400)

    # Rad etish uchun sabab majburiy
    if new_status == 'rejected':
        item.reject_reason = data.get('reject_reason', 'other')
        item.reject_note   = note
        item.save(update_fields=['reject_reason', 'reject_note'])

    item.transition(new_status, request.user, note)
    return JsonResponse({'success': True, 'status': item.status})


@login_required
@require_POST
def lab_item_set_template(request, pk):
    """AJAX: LabOrderItem ga shablon biriktirish"""
    if not _can_edit_lab(request):
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'}, status=403)

    item = get_object_or_404(LabOrderItem, pk=pk)
    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({'success': False, 'error': 'JSON xatosi'}, status=400)

    template_id = data.get('template_id')
    template = get_object_or_404(LabTemplate, pk=template_id)
    item.template = template
    item.save(update_fields=['template'])
    return JsonResponse({'success': True, 'template_name': template.name})


@login_required
@require_POST
def lab_result_create(request, patient_pk):
    """Yangi LabResult yaratish"""
    if not _check_role(request):
        return redirect('patient_list')

    patient = get_object_or_404(PatientCard, pk=patient_pk)
    template_id = request.POST.get('template_id')
    service_ids = request.POST.getlist('service_ids')

    if not template_id:
        return redirect('lab_patient', pk=patient_pk)

    template = get_object_or_404(LabTemplate, pk=template_id)

    lab_result = LabResult.objects.create(
        patient_card=patient,
        template=template,
        status='draft',
        created_by=request.user,
    )

    if service_ids:
        services = PatientService.objects.filter(
            pk__in=service_ids,
            patient_card=patient,
        )
        lab_result.services.set(services)

    return redirect('lab_result_enter', pk=lab_result.pk)


@login_required
def lab_result_enter(request, pk):
    """Natija kiritish sahifasi"""
    if not _check_role(request):
        return redirect('patient_list')

    result = get_object_or_404(
        LabResult.objects.select_related(
            'patient_card', 'template', 'created_by', 'verified_by'
        ),
        pk=pk
    )

    # Parametrlarni guruhlash
    parameters = LabParameter.objects.filter(
        template=result.template
    ).select_related('group').order_by('sort_order', 'name')

    # Mavjud qiymatlarni dict ga o'girish
    existing_values = {
        rv.parameter_id: rv
        for rv in LabResultValue.objects.filter(result=result)
    }

    # Guruhlar bo'yicha parametrlarni guruhlash
    groups_dict = {}
    ungrouped = []
    for param in parameters:
        rv = existing_values.get(param.pk)
        param.current_value = rv.value if rv else ''
        param.current_comment = rv.comment if rv else ''
        param.current_status = rv.value_status if rv else 'normal'
        param.normal_display = param.get_normal_display(result.patient_card.gender)

        if param.group_id:
            gid = param.group_id
            if gid not in groups_dict:
                groups_dict[gid] = {
                    'group': param.group,
                    'params': [],
                }
            groups_dict[gid]['params'].append(param)
        else:
            ungrouped.append(param)

    grouped_params = list(groups_dict.values())

    context = {
        'result': result,
        'grouped_params': grouped_params,
        'ungrouped': ungrouped,
        'can_edit': _can_edit_lab(request),
    }
    return render(request, 'laboratory/lab_result_enter.html', context)


@login_required
@require_POST
def lab_result_save(request, pk):
    """AJAX: Natija qiymatlarini saqlash — faqat admin va laborant"""
    if not _can_edit_lab(request):
        return JsonResponse({'success': False, 'error': 'Faqat laborant yoki admin tahrirlaya oladi'}, status=403)

    result = get_object_or_404(LabResult, pk=pk)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'success': False, 'error': 'JSON xatosi'}, status=400)

    values = data.get('values', [])
    conclusion = data.get('conclusion', '')
    new_status = data.get('status', '')

    for item in values:
        param_id = item.get('param_id')
        value = item.get('value', '')
        comment = item.get('comment', '')

        if not param_id:
            continue

        try:
            parameter = LabParameter.objects.get(pk=param_id, template=result.template)
        except LabParameter.DoesNotExist:
            continue

        # Qiymat holatini aniqlash
        value_status = 'text'
        if parameter.param_type == 'numeric' and value:
            try:
                val_float = float(value)
                low, high = parameter.get_normal_range(result.patient_card.gender)

                # Kritik tekshiruv
                if parameter.critical_min is not None and val_float < float(parameter.critical_min):
                    value_status = 'critical'
                elif parameter.critical_max is not None and val_float > float(parameter.critical_max):
                    value_status = 'critical'
                elif low is not None and val_float < float(low):
                    value_status = 'low'
                elif high is not None and val_float > float(high):
                    value_status = 'high'
                else:
                    value_status = 'normal'
            except (ValueError, TypeError):
                value_status = 'text'
        elif parameter.param_type == 'select':
            value_status = 'text'
        else:
            value_status = 'text'

        LabResultValue.objects.update_or_create(
            result=result,
            parameter=parameter,
            defaults={
                'value': value,
                'value_status': value_status,
                'comment': comment,
            }
        )

    result.conclusion = conclusion

    # Status yangilash
    if new_status in ('draft', 'done', 'verified', 'printed'):
        result.status = new_status
        if new_status == 'verified':
            result.verified_by = request.user
        elif new_status == 'printed':
            result.printed_at = timezone.now()
    elif not new_status:
        # Explicit status berilmasa — to'liqlikka qarab avtomatik
        if result.is_complete:
            result.status = 'done'
        else:
            result.status = 'draft'

    result.save()

    # LabOrderItem statusini sinxronlashtirish
    item = LabOrderItem.objects.filter(result=result).first()
    if item:
        if result.status == 'verified' and item.status != 'verified':
            item.transition('verified', request.user)
        elif result.status == 'done' and item.status in ('result_entering', 'in_progress', 'pending', 'sample_taken'):
            item.transition('completed', request.user)
        elif result.status == 'printed' and item.status != 'printed':
            item.transition('printed', request.user)

    return JsonResponse({
        'success':   True,
        'status':    result.status,
        'complete':  result.is_complete,
        'pct':       result.completion_percent,
    })


@login_required
def lab_result_print(request, pk):
    """Chop etish sahifasi (standalone)"""
    if not _check_role(request):
        return redirect('patient_list')

    result = get_object_or_404(
        LabResult.objects.select_related(
            'patient_card', 'template', 'created_by', 'verified_by',
            'patient_card__department',
        ),
        pk=pk
    )

    # Parametrlar va qiymatlar
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
            'num': i,
            'param': param,
            'value': rv.value if rv else '',
            'value_status': rv.value_status if rv else 'normal',
            'comment': rv.comment if rv else '',
            'normal_display': param.get_normal_display(result.patient_card.gender),
        })

    # Yoshni hisoblash
    birth_date = result.patient_card.birth_date
    today = date.today()
    age = today.year - birth_date.year - (
        (today.month, today.day) < (birth_date.month, birth_date.day)
    )

    # Chop etildi deb belgilash
    if result.status != 'printed':
        result.status = 'printed'
        result.printed_at = timezone.now()
        result.save()

    logo_b64 = ''
    for logo_path in [
        os.path.join(settings.STATIC_ROOT, 'img', 'hospital_logo.png'),
        os.path.join(settings.BASE_DIR, 'static', 'img', 'hospital_logo.png'),
    ]:
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                logo_b64 = base64.b64encode(f.read()).decode()
            break

    context = {
        'result': result,
        'params_with_values': params_with_values,
        'age': age,
        'print_date': date.today(),
        'logo_b64': logo_b64,
    }
    return render(request, 'laboratory/lab_print.html', context)


@login_required
def lab_result_pdf_download(request, pk):
    """PDF ni inline ko'rsatish (browser PDF viewer)."""
    if not _check_role(request):
        return redirect('patient_list')

    result = get_object_or_404(
        LabResult.objects.select_related('patient_card', 'template', 'patient_card__department'),
        pk=pk,
    )

    from apps.telegram_bot.pdf_generator import generate_pdf_bytes
    pdf_bytes = generate_pdf_bytes(result)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="natija_{result.pk}.pdf"'
    return response


def lab_result_pdf_public(request, token):
    """Token orqali ochiq PDF yuklash (bot uchun link)."""
    from apps.telegram_bot.models import ResultFile
    from apps.telegram_bot.pdf_generator import generate_pdf_bytes

    try:
        pdf_file = ResultFile.objects.select_related(
            'lab_result__patient_card', 'lab_result__template',
            'lab_result__patient_card__department',
        ).get(secure_token=token)
    except ResultFile.DoesNotExist:
        return HttpResponse('Havola topilmadi yoki muddati o\'tgan.', status=404)

    if pdf_file.is_expired:
        return HttpResponse('Havolaning muddati tugagan.', status=410)

    pdf_bytes = generate_pdf_bytes(pdf_file.lab_result)
    pdf_file.increment_download()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    fname = f"natija_{pdf_file.lab_result_id}.pdf"
    response['Content-Disposition'] = f'inline; filename="{fname}"'
    return response


@login_required
def lab_template_list(request):
    """Shablonlar ro'yxati"""
    if not _check_role(request):
        return redirect('patient_list')

    templates = LabTemplate.objects.all().order_by('category', 'name')

    # Har bir shablon uchun parametrlar sonini hisoblash
    for tmpl in templates:
        tmpl.param_count = tmpl.parameters.count()

    context = {
        'templates': templates,
        'category_choices': LabTemplate.CATEGORY_CHOICES,
    }
    return render(request, 'laboratory/lab_template_list.html', context)


@login_required
def lab_template_detail(request, pk):
    """Shablon detali va parametrlarni tahrirlash"""
    if not _check_role(request):
        return redirect('patient_list')

    template = get_object_or_404(LabTemplate, pk=pk)
    parameters = LabParameter.objects.filter(
        template=template
    ).select_related('group').order_by('sort_order', 'name')

    groups = LabParameterGroup.objects.filter(template=template).order_by('sort_order')

    context = {
        'template': template,
        'parameters': parameters,
        'groups': groups,
        'param_type_choices': LabParameter.PARAM_TYPE_CHOICES,
    }
    return render(request, 'laboratory/lab_template_detail.html', context)


@login_required
@require_POST
def lab_template_create(request):
    """AJAX: Yangi shablon yaratish"""
    if not _check_role(request):
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'}, status=403)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'success': False, 'error': 'JSON xatosi'}, status=400)

    name = data.get('name', '').strip()
    category = data.get('category', 'other')
    description = data.get('description', '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Nomi kiritilishi shart'}, status=400)

    template = LabTemplate.objects.create(
        name=name,
        category=category,
        description=description,
        is_active=True,
    )

    return JsonResponse({
        'success': True,
        'id': template.pk,
        'name': template.name,
    })


@login_required
@require_POST
def lab_parameter_add(request, template_pk):
    """AJAX: Shablonga parametr qo'shish"""
    if not _check_role(request):
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'}, status=403)

    template = get_object_or_404(LabTemplate, pk=template_pk)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, Exception):
        return JsonResponse({'success': False, 'error': 'JSON xatosi'}, status=400)

    name = data.get('name', '').strip()
    if not name:
        return JsonResponse({'success': False, 'error': 'Nomi kiritilishi shart'}, status=400)

    def to_decimal_or_none(val):
        if val is None or val == '':
            return None
        try:
            return float(val)
        except (ValueError, TypeError):
            return None

    group_id = data.get('group_id')
    group = None
    if group_id:
        try:
            group = LabParameterGroup.objects.get(pk=group_id, template=template)
        except LabParameterGroup.DoesNotExist:
            pass

    parameter = LabParameter.objects.create(
        template=template,
        group=group,
        name=name,
        name_ru=data.get('name_ru', '').strip(),
        unit=data.get('unit', '').strip(),
        param_type=data.get('param_type', 'numeric'),
        normal_min=to_decimal_or_none(data.get('normal_min')),
        normal_max=to_decimal_or_none(data.get('normal_max')),
        critical_min=to_decimal_or_none(data.get('critical_min')),
        critical_max=to_decimal_or_none(data.get('critical_max')),
        normal_min_m=to_decimal_or_none(data.get('normal_min_m')),
        normal_max_m=to_decimal_or_none(data.get('normal_max_m')),
        normal_min_f=to_decimal_or_none(data.get('normal_min_f')),
        normal_max_f=to_decimal_or_none(data.get('normal_max_f')),
        sort_order=int(data.get('sort_order', 0) or 0),
    )

    return JsonResponse({
        'success': True,
        'id': parameter.pk,
        'name': parameter.name,
        'name_ru': parameter.name_ru,
        'unit': parameter.unit,
        'param_type': parameter.param_type,
        'normal_display': parameter.get_normal_display(),
        'sort_order': parameter.sort_order,
    })


@login_required
@require_POST
def lab_parameter_delete(request, pk):
    """AJAX: Parametrni o'chirish"""
    if not _check_role(request):
        return JsonResponse({'success': False, 'error': 'Ruxsat yo\'q'}, status=403)

    parameter = get_object_or_404(LabParameter, pk=pk)
    parameter.delete()

    return JsonResponse({'success': True})
