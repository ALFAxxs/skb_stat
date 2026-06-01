"""
LabResult verified bo'lganda avtomatik bildirishnoma yuborish.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='laboratory.LabResult')
def on_lab_result_save(sender, instance, **kwargs):
    """Natija 'verified' holatiga o'tganda bildirishnoma va PDF yaratish."""
    if instance.status != 'verified':
        return

    from apps.telegram_bot.models import PatientTelegramBinding
    binding = PatientTelegramBinding.objects.filter(
        patient_card=instance.patient_card,
        status='verified',
    ).select_related('telegram_user').first()

    if not binding or binding.telegram_user.is_blocked:
        return

    try:
        from apps.telegram_bot.tasks import send_result_notification, generate_result_pdf
        send_result_notification.delay(
            result_id=instance.pk,
            telegram_user_id=binding.telegram_user.pk,
        )
        generate_result_pdf.delay(result_id=instance.pk)
    except Exception:
        pass