# apps/care/tasks.py
"""
Celery tasks — kechikkan vazifalarni tekshirish va bemorga Telegram orqali
bildirishnoma yuborish. Celery o'rnatilmagan bo'lsa stub sifatida ishlaydi
(apps.telegram_bot.tasks bilan bir xil pattern).
"""

try:
    from celery import shared_task
except ImportError:
    def shared_task(*args, **kwargs):
        def decorator(func):
            func.delay = func
            func.apply_async = lambda *a, **kw: func(*a, **kw)
            return func
        return decorator if args and callable(args[0]) else decorator


@shared_task(name='care.check_overdue_tasks')
def check_overdue_tasks():
    """
    Periodik (Celery beat) ishga tushadi:
      - muddati o'tgan 'pending' vazifalarni 'delayed' ga o'tkazadi
      - juda uzoq 'delayed' vazifalarni 'missed' ga o'tkazadi
    Har bir o'tish uchun Notification va AuditLog yozadi.
    """
    from django.conf import settings
    from django.contrib.contenttypes.models import ContentType
    from django.utils import timezone

    from apps.users.models import CustomUser
    from .models import AuditLog, NurseTask, Notification

    now = timezone.now()
    ct = ContentType.objects.get_for_model(NurseTask)
    status_labels = dict(NurseTask.STATUS_CHOICES)

    delayed_count = 0
    missed_count = 0

    # 1) Muddati o'tgan, hali kutilayotgan vazifalar -> 'delayed'
    overdue_pending = NurseTask.objects.filter(status='pending', scheduled_at__lte=now)
    for task in overdue_pending.select_related('patient_card__department'):
        task.status = 'delayed'
        task.delayed_at = now
        task.save(update_fields=['status', 'delayed_at', 'updated_at'])
        delayed_count += 1

        recipients = CustomUser.objects.filter(role__in=['nurse', 'admin'])
        dept_id = task.patient_card.department_id
        if dept_id:
            from django.db.models import Q
            recipients = recipients.filter(
                Q(department_id=dept_id) | Q(departments=dept_id) | Q(role='admin')
            ).distinct()

        message = f"{task.patient_card.full_name}: {task.title} ({task.scheduled_at:%H:%M})"
        for user in recipients:
            Notification.objects.create(
                recipient=user, patient_card=task.patient_card,
                notification_type='task_delayed',
                title="Vazifa kechikdi",
                message=message,
                priority='urgent',
                content_type=ct, object_id=task.pk,
            )

        AuditLog.objects.create(
            actor=None, patient_card=task.patient_card,
            content_type=ct, object_id=task.pk,
            action='status_changed', field_name='status',
            old_value='pending', new_value='delayed',
            description=f"Vazifa avtomatik kechiktirildi: {status_labels['pending']} → {status_labels['delayed']}",
        )

    # 2) Juda uzoq 'delayed' bo'lgan vazifalar -> 'missed'
    missed_after = getattr(settings, 'CARE_TASK_MISSED_AFTER_MINUTES', 120)
    threshold = now - timezone.timedelta(minutes=missed_after)
    long_delayed = NurseTask.objects.filter(status='delayed', scheduled_at__lte=threshold)
    for task in long_delayed:
        task.status = 'missed'
        task.save(update_fields=['status', 'updated_at'])
        missed_count += 1

        AuditLog.objects.create(
            actor=None, patient_card=task.patient_card,
            content_type=ct, object_id=task.pk,
            action='status_changed', field_name='status',
            old_value='delayed', new_value='missed',
            description=f"Vazifa avtomatik o'tkazib yuborildi: {status_labels['delayed']} → {status_labels['missed']}",
        )

    return {'delayed': delayed_count, 'missed': missed_count}


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name='care.deliver_patient_telegram_notification')
def deliver_patient_telegram_notification(self, notification_id: int):
    """Bemorga (agar Telegram bog'langan bo'lsa) bildirishnoma yuborish."""
    from django.conf import settings

    from apps.telegram_bot.models import PatientTelegramBinding
    from .models import Notification

    try:
        notif = Notification.objects.select_related('patient_card').get(pk=notification_id)
        if not notif.patient_card_id:
            return

        binding = PatientTelegramBinding.objects.select_related('telegram_user').filter(
            patient_card_id=notif.patient_card_id, status='verified',
        ).first()
        if not binding or binding.telegram_user.is_blocked:
            return

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            return

        import urllib.request, json as _json

        text = f"\U0001F514 <b>{notif.title}</b>\n\n{notif.message}"
        payload = {
            "chat_id": binding.telegram_user.telegram_id,
            "text": text,
            "parse_mode": "HTML",
        }
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            _json.loads(resp.read())

    except Exception as exc:
        raise self.retry(exc=exc)
