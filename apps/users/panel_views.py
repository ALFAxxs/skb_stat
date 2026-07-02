# apps/users/panel_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext as _
from django.db.models import Q, Count

from .decorators import role_required
from .models import CustomUser
from apps.patients.models import Department
from apps.services.models import ServiceCategory, Service, Medicine
from apps.laboratory.models import LabTemplate, LabParameter


def _admin_only(func):
    return login_required(role_required('admin')(func))


# ─────────────────────────────── Dashboard ────────────────────────────────────

@_admin_only
def panel_dashboard(request):
    from apps.users.models import CustomUser
    stats = {
        'users':       CustomUser.objects.count(),
        'departments': Department.objects.count(),
        'categories':  ServiceCategory.objects.count(),
        'services':    Service.objects.count(),
        'medicines':   Medicine.objects.count(),
        'lab_templates': LabTemplate.objects.count(),
    }
    return render(request, 'panel/dashboard.html', {'stats': stats})


# ─────────────────────────────── Bo'limlar ───────────────────────────────────

@_admin_only
def panel_departments(request):
    q = request.GET.get('q', '').strip()
    qs = Department.objects.all().order_by('name')
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, 'panel/departments.html', {'departments': qs, 'q': q})


@_admin_only
@require_POST
def panel_department_save(request, pk=None):
    name = request.POST.get('name', '').strip()
    if not name:
        messages.error(request, _("Nom kiritilishi shart."))
        return redirect('panel_departments')
    if pk:
        dept = get_object_or_404(Department, pk=pk)
        dept.name = name
        dept.save()
        messages.success(request, _("Bo'lim yangilandi."))
    else:
        Department.objects.create(name=name)
        messages.success(request, _("Bo'lim qo'shildi."))
    return redirect('panel_departments')


@_admin_only
@require_POST
def panel_department_toggle(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.is_active = not dept.is_active
    dept.save()
    return redirect('panel_departments')


@_admin_only
@require_POST
def panel_department_delete(request, pk):
    dept = get_object_or_404(Department, pk=pk)
    dept.delete()
    messages.success(request, _("Bo'lim o'chirildi."))
    return redirect('panel_departments')


# ────────────────────────── Xizmat kategoriyalari ────────────────────────────

@_admin_only
def panel_categories(request):
    q = request.GET.get('q', '').strip()
    qs = ServiceCategory.objects.annotate(service_count=Count('services')).order_by('category_type', 'name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    return render(request, 'panel/categories.html', {
        'categories': qs,
        'q': q,
        'type_choices': ServiceCategory.CATEGORY_TYPE_CHOICES,
    })


@_admin_only
@require_POST
def panel_category_save(request, pk=None):
    name          = request.POST.get('name', '').strip()
    name_ru       = request.POST.get('name_ru', '').strip()
    code          = request.POST.get('code', '').strip()
    category_type = request.POST.get('category_type', 'other')
    icon          = request.POST.get('icon', '🏥').strip() or '🏥'
    is_active     = request.POST.get('is_active') == '1'

    if not name:
        messages.error(request, _("Nom kiritilishi shart."))
        return redirect('panel_categories')

    if pk:
        cat = get_object_or_404(ServiceCategory, pk=pk)
        cat.name = name; cat.name_ru = name_ru; cat.code = code
        cat.category_type = category_type; cat.icon = icon; cat.is_active = is_active
        cat.save()
        messages.success(request, _("Kategoriya yangilandi."))
    else:
        ServiceCategory.objects.create(
            name=name, name_ru=name_ru, code=code,
            category_type=category_type, icon=icon, is_active=is_active,
        )
        messages.success(request, _("Kategoriya qo'shildi."))
    return redirect('panel_categories')


@_admin_only
@require_POST
def panel_category_delete(request, pk):
    cat = get_object_or_404(ServiceCategory, pk=pk)
    cat.delete()
    messages.success(request, _("Kategoriya o'chirildi."))
    return redirect('panel_categories')


# ──────────────────────────────── Xizmatlar ──────────────────────────────────

@_admin_only
def panel_services(request):
    import json
    q       = request.GET.get('q', '').strip()
    cat_id  = request.GET.get('cat', '')
    qs = Service.objects.select_related('category', 'department').prefetch_related('assigned_doctors__department').order_by('category__name', 'name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if cat_id:
        qs = qs.filter(category_id=cat_id)

    services_list = list(qs)
    for s in services_list:
        docs = s.assigned_doctors.all()
        s.doc_pks_json  = json.dumps([d.pk for d in docs])
        s.doc_info_json = json.dumps([
            {'pk': d.pk, 'name': d.get_full_name() or d.username,
             'dept': d.department.name if d.department_id else ''}
            for d in docs
        ])

    categories  = ServiceCategory.objects.filter(is_active=True).order_by('name')
    departments = Department.objects.filter(is_active=True).order_by('name')
    doctors     = CustomUser.objects.filter(role='doctor', is_active=True).order_by('last_name', 'first_name')
    return render(request, 'panel/services.html', {
        'services': services_list, 'q': q, 'cat_id': cat_id,
        'categories': categories, 'departments': departments,
        'doctors': doctors,
    })


@_admin_only
@require_POST
def panel_service_save(request, pk=None):
    name          = request.POST.get('name', '').strip()
    name_ru       = request.POST.get('name_ru', '').strip()
    code          = request.POST.get('code', '').strip()
    category_id   = request.POST.get('category_id')
    department_id = request.POST.get('department_id') or None
    price_normal  = request.POST.get('price_normal', '0') or '0'
    price_railway = request.POST.get('price_railway', '0') or '0'
    is_active     = request.POST.get('is_active') == '1'
    is_operation  = request.POST.get('is_operation') == '1'
    doctor_ids    = request.POST.getlist('assigned_doctors')

    if not name or not category_id:
        messages.error(request, _("Nomi va kategoriya kiritilishi shart."))
        return redirect('panel_services')

    fields = dict(
        name=name, name_ru=name_ru, code=code,
        category_id=category_id, department_id=department_id,
        price_normal=price_normal, price_railway=price_railway,
        is_active=is_active, is_operation=is_operation,
    )
    if pk:
        svc = get_object_or_404(Service, pk=pk)
        for k, v in fields.items():
            setattr(svc, k, v)
        svc.save()
        svc.assigned_doctors.set(doctor_ids)
        messages.success(request, _("Xizmat yangilandi."))
    else:
        svc = Service.objects.create(**fields)
        svc.assigned_doctors.set(doctor_ids)
        messages.success(request, _("Xizmat qo'shildi."))
    return redirect(request.POST.get('next') or 'panel_services')


@_admin_only
@require_POST
def panel_service_toggle(request, pk):
    svc = get_object_or_404(Service, pk=pk)
    svc.is_active = not svc.is_active
    svc.save()
    return redirect('panel_services')


@_admin_only
@require_POST
def panel_service_delete(request, pk):
    svc = get_object_or_404(Service, pk=pk)
    svc.delete()
    messages.success(request, _("Xizmat o'chirildi."))
    return redirect('panel_services')


# ──────────────────────────────── Dorilar ────────────────────────────────────

@_admin_only
def panel_medicines(request):
    q        = request.GET.get('q', '').strip()
    category = request.GET.get('cat', '')
    qs = Medicine.objects.order_by('name')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(mnn__icontains=q))
    if category:
        qs = qs.filter(category=category)
    return render(request, 'panel/medicines.html', {
        'medicines': qs, 'q': q, 'cat': category,
        'unit_choices':        Medicine.UNIT_CHOICES,
        'dosage_form_choices': Medicine.DOSAGE_FORM_CHOICES,
        'category_choices':    Medicine.CATEGORY_CHOICES,
    })


@_admin_only
@require_POST
def panel_medicine_save(request, pk=None):
    name        = request.POST.get('name', '').strip()
    mnn         = request.POST.get('mnn', '').strip()
    dosage_form = request.POST.get('dosage_form', '')
    strength    = request.POST.get('strength', '').strip()
    unit        = request.POST.get('unit', 'dona')
    category    = request.POST.get('category', 'drug')
    is_active   = request.POST.get('is_active') == '1'

    if not name:
        messages.error(request, _("Nom kiritilishi shart."))
        return redirect('panel_medicines')

    fields = dict(name=name, mnn=mnn, dosage_form=dosage_form,
                  strength=strength, unit=unit, category=category, is_active=is_active)
    if pk:
        med = get_object_or_404(Medicine, pk=pk)
        for k, v in fields.items():
            setattr(med, k, v)
        med.save()
        messages.success(request, _("Dori yangilandi."))
    else:
        Medicine.objects.create(**fields)
        messages.success(request, _("Dori qo'shildi."))
    return redirect('panel_medicines')


@_admin_only
@require_POST
def panel_medicine_toggle(request, pk):
    med = get_object_or_404(Medicine, pk=pk)
    med.is_active = not med.is_active
    med.save()
    return redirect('panel_medicines')


@_admin_only
@require_POST
def panel_medicine_delete(request, pk):
    med = get_object_or_404(Medicine, pk=pk)
    med.delete()
    messages.success(request, _("Dori o'chirildi."))
    return redirect('panel_medicines')


# ─────────────────────────── Lab shablonlari ─────────────────────────────────

@_admin_only
def panel_lab_templates(request):
    q = request.GET.get('q', '').strip()
    qs = LabTemplate.objects.annotate(param_count=Count('parameters')).order_by('category', 'name')
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, 'panel/lab_templates.html', {
        'templates': qs, 'q': q,
        'category_choices': LabTemplate.CATEGORY_CHOICES,
    })


@_admin_only
@require_POST
def panel_lab_template_save(request, pk=None):
    name        = request.POST.get('name', '').strip()
    category    = request.POST.get('category', 'other')
    description = request.POST.get('description', '').strip()
    is_active   = request.POST.get('is_active') == '1'

    if not name:
        messages.error(request, _("Nom kiritilishi shart."))
        return redirect('panel_lab_templates')

    if pk:
        tmpl = get_object_or_404(LabTemplate, pk=pk)
        tmpl.name = name; tmpl.category = category
        tmpl.description = description; tmpl.is_active = is_active
        tmpl.save()
        messages.success(request, _("Shablon yangilandi."))
    else:
        LabTemplate.objects.create(name=name, category=category,
                                   description=description, is_active=is_active)
        messages.success(request, _("Shablon qo'shildi."))
    return redirect('panel_lab_templates')


@_admin_only
@require_POST
def panel_lab_template_toggle(request, pk):
    tmpl = get_object_or_404(LabTemplate, pk=pk)
    tmpl.is_active = not tmpl.is_active
    tmpl.save()
    return redirect('panel_lab_templates')


@_admin_only
@require_POST
def panel_lab_template_delete(request, pk):
    tmpl = get_object_or_404(LabTemplate, pk=pk)
    tmpl.delete()
    messages.success(request, _("Shablon o'chirildi."))
    return redirect('panel_lab_templates')
