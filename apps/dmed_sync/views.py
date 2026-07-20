"""
DMED Sync monitoring paneli — admin uchun.
"""
import asyncio
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.shortcuts import render

from .models import DMEDSyncRecord


def _admin_only(view_fn):
    from apps.users.decorators import role_required
    from functools import wraps
    @login_required
    @role_required('admin')
    @wraps(view_fn)
    def wrapper(*a, **kw):
        return view_fn(*a, **kw)
    return wrapper


@_admin_only
def monitor(request):
    status_filter = request.GET.get('status', '')
    entity_filter = request.GET.get('entity', '')

    qs = DMEDSyncRecord.objects.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if entity_filter:
        qs = qs.filter(entity_type=entity_filter)
    qs = qs.order_by('-enqueued_at')[:200]

    counts = {
        'pending': DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_PENDING).count(),
        'running': DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_RUNNING).count(),
        'done':    DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_DONE).count(),
        'failed':  DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_FAILED).count(),
    }

    from django.conf import settings
    from .models import DMEDSession
    dmed_enabled = getattr(settings, 'DMED_SYNC_ENABLED', False)
    session      = DMEDSession.get_latest()

    return render(request, 'dmed_sync/monitor.html', {
        'records':        qs,
        'counts':         counts,
        'status_filter':  status_filter,
        'entity_filter':  entity_filter,
        'status_choices': DMEDSyncRecord.STATUS_CHOICES,
        'entity_choices': DMEDSyncRecord.ENTITY_CHOICES,
        'dmed_enabled':   dmed_enabled,
        'session':        session,
    })


@_admin_only
@require_POST
def retry_record(request, pk):
    """Xato yozuvni qayta navbatga qo'yish."""
    record = get_object_or_404(DMEDSyncRecord, pk=pk)
    record.status   = DMEDSyncRecord.STATUS_PENDING
    record.attempts = 0
    record.error    = ''
    record.save(update_fields=['status', 'attempts', 'error'])
    messages.success(request, f'#{pk} qayta navbatga qo\'yildi.')
    return redirect('dmed_monitor')


@_admin_only
@require_POST
def retry_all_failed(request):
    """Barcha xato yozuvlarni qayta navbatga qo'yish."""
    n = DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_FAILED).update(
        status=DMEDSyncRecord.STATUS_PENDING,
        attempts=0,
        error='',
    )
    messages.success(request, f'{n} ta xato yozuv qayta navbatga qo\'yildi.')
    return redirect('dmed_monitor')


@_admin_only
@require_POST
def run_now(request):
    """Workerga qaramasdan hozir darhol pending'larni ishlatish."""
    from .tasks import run_pending
    try:
        run_pending()
        messages.success(request, 'Sinxronizatsiya tugadi.')
    except Exception as exc:
        messages.error(request, f'Xato: {exc}')
    return redirect('dmed_monitor')


@_admin_only
def status_json(request):
    """AJAX — monitoring sahifasi uchun live statistika."""
    return JsonResponse({
        'pending': DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_PENDING).count(),
        'running': DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_RUNNING).count(),
        'done':    DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_DONE).count(),
        'failed':  DMEDSyncRecord.objects.filter(status=DMEDSyncRecord.STATUS_FAILED).count(),
    })
