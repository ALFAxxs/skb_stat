"""
DMED Sync monitoring paneli — admin uchun.
"""
import asyncio
import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.shortcuts import render

from .models import DMEDSyncRecord, DMEDLoginAttempt


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


# ─── Web-based DMED Login ─────────────────────────────────────────────────────

@_admin_only
def dmed_login_page(request):
    """DMED Login sahifasi — PINFL va OTP kiritish."""
    from .models import DMEDSession
    session = DMEDSession.get_latest()
    return render(request, 'dmed_sync/login.html', {'session': session})


@_admin_only
def dmed_login_start(request):
    """POST: PINFL bilan login boshlash → Celery task ishga tushiradi."""
    if request.method != 'POST':
        return JsonResponse({'ok': False})

    pinfl = request.POST.get('pinfl', '').strip()
    if not pinfl or len(pinfl) != 14 or not pinfl.isdigit():
        return JsonResponse({'ok': False, 'error': "PINFL 14 ta raqamdan iborat bo'lishi kerak"})

    attempt = DMEDLoginAttempt.objects.create()
    from .login_task import dmed_web_login_task
    dmed_web_login_task.delay(pinfl, attempt.id, by_user=request.user.username)
    return JsonResponse({'ok': True, 'attempt_id': attempt.id})


@_admin_only
def dmed_login_status(request, pk):
    """GET: Login jarayoni holati (polling uchun)."""
    attempt = get_object_or_404(DMEDLoginAttempt, pk=pk)
    return JsonResponse({'status': attempt.status, 'error': attempt.error})


@_admin_only
@require_POST
def dmed_login_otp(request, pk):
    """POST: SMS OTP kodni yuborish → task ni davom ettiradi."""
    attempt = get_object_or_404(DMEDLoginAttempt, pk=pk)
    if attempt.status != DMEDLoginAttempt.ST_WAIT_OTP:
        return JsonResponse({'ok': False, 'error': 'SMS kod hali kutilmayapti'})

    otp = request.POST.get('otp', '').strip()
    if not otp or len(otp) != 5 or not otp.isdigit():
        return JsonResponse({'ok': False, 'error': '5 ta raqamdan iborat kod kiriting'})

    attempt.otp_code = otp
    attempt.save(update_fields=['otp_code'])
    return JsonResponse({'ok': True})


@_admin_only
@require_POST
def dmed_session_import(request):
    """POST: Lokal kompyuterdan eksport qilingan session JSON ni saqlash."""
    raw = request.POST.get('session_json', '').strip()
    if not raw:
        return JsonResponse({'ok': False, 'error': 'JSON bo\'sh'})

    try:
        state = json.loads(raw)
    except json.JSONDecodeError as e:
        return JsonResponse({'ok': False, 'error': f'JSON format xato: {e}'})

    if not isinstance(state, dict) or 'cookies' not in state:
        return JsonResponse({
            'ok': False,
            'error': "Noto'g'ri format — Playwright storage_state (cookies + origins) kutilmoqda"
        })

    from .models import DMEDSession
    DMEDSession.save_state(state, logged_in_by=request.user.username)
    return JsonResponse({'ok': True})
