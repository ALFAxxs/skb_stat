# apps/queue_app/models.py

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class QueueTicket(models.Model):
    STATUS_CHOICES = [
        ('waiting',   _('Kutmoqda')),
        ('calling',   _('Chaqirilmoqda')),
        ('serving',   _("Xizmat ko'rilmoqda")),
        ('done',      _('Yakunlandi')),
        ('skipped',   _("O'tkazib yuborildi")),
    ]

    ticket_number = models.PositiveIntegerField(verbose_name=_("Navbat raqami"))
    patient_card  = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='queue_tickets', verbose_name=_("Bemor")
    )
    service       = models.ForeignKey(
        'services.PatientService', on_delete=models.CASCADE,
        related_name='queue_ticket', verbose_name=_("Xizmat"),
        null=True, blank=True
    )
    status        = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='waiting', verbose_name=_("Holat")
    )
    room          = models.CharField(max_length=50, default='MRT xonasi', verbose_name=_("Xona"))
    created_at    = models.DateTimeField(auto_now_add=True)
    called_at     = models.DateTimeField(null=True, blank=True)
    served_at     = models.DateTimeField(null=True, blank=True)
    done_at       = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = _("Navbat chipta")
        verbose_name_plural = _("Navbat chiptalar")
        ordering            = ['ticket_number']

    def __str__(self):
        return f"#{self.ticket_number} — {self.patient_card.full_name} ({self.get_status_display()})"

    @classmethod
    def next_ticket_number(cls):
        today = timezone.now().date()
        last  = cls.objects.filter(created_at__date=today).order_by('-ticket_number').first()
        return (last.ticket_number + 1) if last else 1

    @classmethod
    def current_calling(cls):
        return cls.objects.filter(status='calling').order_by('-called_at').first()

    @classmethod
    def today_waiting(cls):
        today = timezone.now().date()
        return cls.objects.filter(created_at__date=today, status='waiting').order_by('ticket_number')


class QueueSettings(models.Model):
    AUDIO_CHOICES = [
        ('beep',  _('🔔 Signal (ding)')),
        ('voice', _('🔊 Ovozli chaqiruv')),
        ('both',  _('🔔🔊 Ikkalasi')),
        ('off',   _('🔇 Ovozsiz')),
    ]
    audio_mode = models.CharField(
        max_length=10, choices=AUDIO_CHOICES,
        default='beep', verbose_name=_("Audio rejim")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Navbat sozlamalari")
        verbose_name_plural = _("Navbat sozlamalari")

    @classmethod
    def get(cls):
        """Yagona sozlamalar ob'ektini qaytaradi"""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj