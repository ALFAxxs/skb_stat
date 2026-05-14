# apps/results/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils import timezone

from apps.results.models import ResultTemplate, ServiceResult
from apps.services.models import PatientService


# ===== SHABLONLAR =====

@login_required
def template_list(request):
    """Barcha shablonlar ro'yxati"""
    templates = ResultTemplate.objects.filter(is_active=True)
    category  = request.GET.get('category', '')
    if category:
        templates = templates.filter(category=category)
    return render(request, 'results/template_list.html', {
        'templates': templates,
        'categories': ResultTemplate.CATEGORY_CHOICES,
        'current_category': category,
    })


@login_required
def template_create(request):
    """Yangi shablon yaratish"""
    if request.method == 'POST':
        name     = request.POST.get('name', '').strip()
        category = request.POST.get('category', 'other')
        content  = request.POST.get('content', '').strip()
        description = request.POST.get('description', '').strip()

        if not name or not content:
            messages.error(request, "Nom va kontent majburiy.")
            return redirect('result_template_create')

        t = ResultTemplate.objects.create(
            name=name, category=category,
            content=content, description=description,
            created_by=request.user
        )
        messages.success(request, f"✅ Shablon yaratildi: {t.name}")
        return redirect('result_template_list')

    return render(request, 'results/template_form.html', {
        'categories': ResultTemplate.CATEGORY_CHOICES,
        'action': 'create',
    })


@login_required
def template_edit(request, pk):
    """Shablonni tahrirlash"""
    template = get_object_or_404(ResultTemplate, pk=pk)

    if request.method == 'POST':
        template.name        = request.POST.get('name', '').strip()
        template.category    = request.POST.get('category', 'other')
        template.content     = request.POST.get('content', '').strip()
        template.description = request.POST.get('description', '').strip()
        template.save()
        messages.success(request, "✅ Shablon yangilandi.")
        return redirect('result_template_list')

    return render(request, 'results/template_form.html', {
        'template': template,
        'categories': ResultTemplate.CATEGORY_CHOICES,
        'action': 'edit',
    })


@login_required
@require_POST
def template_delete(request, pk):
    template = get_object_or_404(ResultTemplate, pk=pk)
    template.is_active = False
    template.save()
    messages.success(request, "Shablon o'chirildi.")
    return redirect('result_template_list')


@login_required
def template_get(request, pk):
    """AJAX — shablon kontent qaytarish"""
    template = get_object_or_404(ResultTemplate, pk=pk, is_active=True)
    return JsonResponse({'content': template.content, 'name': template.name})


# ===== NATIJALAR =====

@login_required
def result_create(request, service_pk):
    """Xizmat natijasini kiritish"""
    patient_service = get_object_or_404(PatientService, pk=service_pk)

    # Mavjud natija bo'lsa — tahrirlashga yo'naltirish
    if hasattr(patient_service, 'result'):
        return redirect('result_edit', pk=patient_service.result.pk)

    templates = ResultTemplate.objects.filter(is_active=True).order_by('category', 'name')

    if request.method == 'POST':
        content     = request.POST.get('content', '').strip()
        template_id = request.POST.get('template_id')
        status      = request.POST.get('status', 'draft')

        if not content:
            messages.error(request, "Natija bo'sh bo'lishi mumkin emas.")
        else:
            ServiceResult.objects.create(
                patient_service = patient_service,
                template_id     = template_id or None,
                content         = content,
                status          = status,
                created_by      = request.user,
                updated_by      = request.user,
            )
            messages.success(request, "✅ Natija saqlandi.")
            return redirect('patient_detail', pk=patient_service.patient_card.pk)

    return render(request, 'results/result_form.html', {
        'patient_service': patient_service,
        'patient':         patient_service.patient_card,
        'templates':       templates,
        'action':          'create',
    })


@login_required
def result_edit(request, pk):
    """Natijani tahrirlash"""
    result      = get_object_or_404(ServiceResult, pk=pk)
    templates   = ResultTemplate.objects.filter(is_active=True).order_by('category', 'name')

    if request.method == 'POST':
        result.content    = request.POST.get('content', '').strip()
        result.status     = request.POST.get('status', 'draft')
        result.updated_by = request.user
        template_id       = request.POST.get('template_id')
        if template_id:
            result.template_id = template_id
        result.save()
        messages.success(request, "✅ Natija yangilandi.")
        return redirect('patient_detail', pk=result.patient.pk)

    return render(request, 'results/result_form.html', {
        'result':          result,
        'patient_service': result.patient_service,
        'patient':         result.patient,
        'templates':       templates,
        'action':          'edit',
    })


@login_required
def result_view(request, pk):
    """Natijani ko'rish (chop etish uchun)"""
    result = get_object_or_404(ServiceResult, pk=pk)
    return render(request, 'results/result_view.html', {
        'result':  result,
        'patient': result.patient,
    })


@login_required
def result_print(request, pk):
    """Chop etish sahifasi"""
    result = get_object_or_404(ServiceResult, pk=pk)
    return render(request, 'results/result_print.html', {
        'result':  result,
        'patient': result.patient,
    })
