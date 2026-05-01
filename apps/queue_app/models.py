# apps/queue/models.py

from django.db import models
from django.utils import timezone


class QueueTicket(models.Model):
    STATUS_CHOICES = [
        ('waiting',   'Kutmoqda'),
        ('calling',   'Chaqirilmoqda'),
        ('serving',   'Xizmat ko\'rilmoqda'),
        ('done',      'Yakunlandi'),
        ('skipped',   'O\'tkazib yuborildi'),
    ]

    ticket_number   = models.PositiveIntegerField(verbose_name="Navbat raqami")
    patient_card    = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='queue_tickets', verbose_name="Bemor"
    )
    service         = models.ForeignKey(
        'services.PatientService', on_delete=models.CASCADE,
        related_name='queue_ticket', verbose_name="Xizmat",
        null=True, blank=True
    )
    status          = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='waiting', verbose_name="Holat"
    )
    room            = models.CharField(
        max_length=50, default='MRT xonasi',
        verbose_name="Xona"
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    called_at       = models.DateTimeField(null=True, blank=True)
    served_at       = models.DateTimeField(null=True, blank=True)
    done_at         = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = "Navbat chipta"
        verbose_name_plural = "Navbat chiptalar"
        ordering            = ['ticket_number']

    def __str__(self):
        return f"#{self.ticket_number} — {self.patient_card.full_name} ({self.get_status_display()})"

    @classmethod
    def next_ticket_number(cls):
        """Bugungi navbat raqami"""
        today = timezone.now().date()
        last = cls.objects.filter(created_at__date=today).order_by('-ticket_number').first()
        return (last.ticket_number + 1) if last else 1

    @classmethod
    def current_calling(cls):
        """Hozir chaqirilayotgan bemor"""
        return cls.objects.filter(status='calling').order_by('-called_at').first()

    @classmethod
    def today_waiting(cls):
        """Bugun kutayotganlar"""
        today = timezone.now().date()
        return cls.objects.filter(
            created_at__date=today,
            status='waiting'
        ).order_by('ticket_number')