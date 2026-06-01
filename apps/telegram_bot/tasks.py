"""
Celery tasks — bildirishnomalar va PDF generatsiya.
Celery o'rnatilmagan bo'lsa stub sifatida ishlaydi.
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


@shared_task(bind=True, max_retries=3, default_retry_delay=60, name='bot.send_result_notification')
def send_result_notification(self, result_id: int, telegram_user_id: int):
    """Telegram orqali natija bildirishnomasi yuborish."""
    from django.conf import settings
    from django.utils import timezone
    from apps.laboratory.models import LabResult
    from apps.telegram_bot.models import TelegramUser, ResultNotification

    try:
        result = LabResult.objects.select_related('template', 'patient_card').get(pk=result_id)
        tg_user = TelegramUser.objects.get(pk=telegram_user_id)

        if tg_user.is_blocked:
            return

        notif, created = ResultNotification.objects.get_or_create(
            telegram_user=tg_user,
            lab_result=result,
            defaults={'status': 'pending'},
        )

        if not created and notif.status == 'sent':
            return  # Allaqachon yuborilgan

        bot_token = settings.TELEGRAM_BOT_TOKEN
        if not bot_token:
            notif.mark_failed('BOT_TOKEN sozlanmagan')
            return

        import urllib.request, json as _json

        text = (
            f"🔔 <b>Analiz natijangiz tayyor!</b>\n\n"
            f"🧪 {result.template.name}\n"
            f"📅 {result.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Ko'rish yoki PDF yuklab olish uchun botga kiring."
        )

        payload = {
            "chat_id":      tg_user.telegram_id,
            "text":         text,
            "parse_mode":   "HTML",
            "protect_content": True,
            "reply_markup": _json.dumps({
                "inline_keyboard": [[
                    {"text": "👁 Ko'rish",   "callback_data": f"result:{result_id}"},
                    {"text": "📥 PDF",        "callback_data": f"pdf:{result_id}"},
                ]]
            })
        }

        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read())

        if data.get('ok'):
            notif.mark_sent(data['result']['message_id'])
        else:
            notif.mark_failed(str(data))

    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(name='bot.generate_result_pdf')
def generate_result_pdf(result_id: int):
    """PDF fayl generatsiya qilish."""
    from django.utils import timezone
    from datetime import timedelta
    from apps.laboratory.models import LabResult
    from apps.telegram_bot.models import ResultFile
    from apps.telegram_bot.pdf_generator import generate_pdf

    try:
        result = LabResult.objects.select_related(
            'template', 'patient_card', 'created_by', 'verified_by'
        ).get(pk=result_id)

        pdf_file, created = ResultFile.objects.get_or_create(
            lab_result=result,
            defaults={'expires_at': timezone.now() + timedelta(days=30)},
        )

        # Agar muddati o'tgan bo'lsa — qayta yaratish
        if not created and pdf_file.is_expired:
            pdf_file.file_path        = ''
            pdf_file.telegram_file_id = ''
            pdf_file.expires_at       = timezone.now() + timedelta(days=30)

        if not pdf_file.file_path:
            filepath          = generate_pdf(result)
            pdf_file.file_path = filepath

        pdf_file.save()

    except LabResult.DoesNotExist:
        pass
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"PDF generatsiya xatosi: {e}")