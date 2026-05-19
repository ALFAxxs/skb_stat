# apps/laboratory/views.py

import json
from datetime import date, datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.patients.models import PatientCard
from apps.services.models import PatientService

from .models import (
    LabParameter,
    LabParameterGroup,
    LabResult,
    LabResultValue,
    LabTemplate,
)


def _check_role(request):
    """Lab sahifalariga kirish huquqi: admin, doctor, laborant."""
    return request.user.is_superuser or request.user.role in ('admin', 'doctor', 'laborant')

def _can_edit_lab(request):
    """Natijani tahrirlash huquqi: faqat admin va laborant."""
    return request.user.is_superuser or request.user.role in ('admin', 'laborant')


@login_required
def lab_home(request):
    """Bugungi lab buyurtmalar ro'yxati, bemorlar bo'yicha guruhlangan"""
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

    # Faqat lab kategoriyasidagi xizmatlar
    lab_services = PatientService.objects.filter(
        service__category__category_type='lab',
        ordered_at__date=filter_date,
    ).select_related(
        'patient_card', 'service', 'service__category'
    ).order_by('patient_card__full_name')

    # Bemorlar bo'yicha guruhlash
    patients_dict = {}
    for ps in lab_services:
        pk = ps.patient_card_id
        if pk not in patients_dict:
            patients_dict[pk] = {
                'patient': ps.patient_card,
                'services': [],
            }
        patients_dict[pk]['services'].append(ps)

    # Har bir bemor uchun mavjud natijalar sonini hisoblash
    patients_list = []
    for pk, data in patients_dict.items():
        result_count = LabResult.objects.filter(patient_card_id=pk).count()
        patients_list.append({
            'patient': data['patient'],
            'services': data['services'],
            'result_count': result_count,
        })

    context = {
        'patients_list': patients_list,
        'filter_date': filter_date,
        'today': date.today(),
    }
    return render(request, 'laboratory/lab_home.html', context)


@login_required
def lab_patient(request, pk):
    """Bemorning barcha lab xizmatlari va natijalari"""
    if not _check_role(request):
        return redirect('patient_list')

    patient = get_object_or_404(PatientCard, pk=pk)

    # Bemorning barcha lab xizmatlari
    lab_services = PatientService.objects.filter(
        patient_card=patient,
        service__category__category_type='lab',
    ).select_related('service', 'service__category').order_by('-ordered_at')

    # Mavjud natijalar
    existing_results = LabResult.objects.filter(
        patient_card=patient
    ).select_related('template').order_by('-created_at')

    # Faol shablonlar
    templates = LabTemplate.objects.filter(is_active=True).order_by('category', 'name')

    context = {
        'patient': patient,
        'lab_services': lab_services,
        'existing_results': existing_results,
        'templates': templates,
        'can_edit': _can_edit_lab(request),
    }
    return render(request, 'laboratory/lab_patient.html', context)


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

    if conclusion:
        result.conclusion = conclusion

    if new_status in ('draft', 'done', 'verified', 'printed'):
        result.status = new_status
        if new_status == 'verified':
            result.verified_by = request.user

    result.save()

    return JsonResponse({'success': True, 'status': result.status})


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

    context = {
        'result': result,
        'params_with_values': params_with_values,
        'age': age,
        'print_date': date.today(),
    }
    return render(request, 'laboratory/lab_print.html', context)


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
