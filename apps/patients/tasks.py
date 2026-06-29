# apps/patients/tasks.py
"""
Celery tasks — ServiceSchedule bandlari uchun eslatma yuborish.
Bu vazifa `doctor_notifications_ajax` polling'idagi xuddi shu sweep'ning
backstop nusxasi — hech kim dashboard ochiq holda polling qilmayotganda ham
(masalan tungi navbatda) eslatmalar o'z vaqtida yuborilishini ta'minlaydi.
Celery o'rnatilmagan bo'lsa stub sifatida ishlaydi (apps.care.tasks bilan bir xil pattern).
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


@shared_task(name='patients.send_due_schedule_reminders')
def send_due_schedule_reminders():
    from apps.patients.views import _send_due_schedule_reminders
    _send_due_schedule_reminders()
