# apps/contracts/models.py

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.patients.models import PatientCard


class Contract(models.Model):
    STATUS_CHOICES = [
        ('draft',     _('Loyiha')),
        ('active',    _('Faol')),
        ('cancelled', _('Bekor qilingan')),
    ]
    TYPE_CHOICES = [
        ('paid',         _('Pullik')),
        ('non_resident', _('Norezident')),
    ]

    patient_card     = models.OneToOneField(
        PatientCard, on_delete=models.CASCADE,
        related_name='contract', verbose_name=_("Bemor kartasi")
    )
    contract_number  = models.CharField(max_length=30, unique=True, verbose_name=_("Shartnoma raqami"))
    contract_date    = models.DateField(verbose_name=_("Shartnoma sanasi"))
    contract_type    = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_("Turi"))
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                        default='active', verbose_name=_("Holati"))
    verify_token     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pdf_file         = models.FileField(upload_to='contracts/', blank=True, null=True,
                                        verbose_name=_("PDF fayl"))
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Shartnoma")
        verbose_name_plural = _("Shartnomalar")
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contract_number} — {self.patient_card.full_name}"

    @property
    def verify_url(self):
        return f"/contracts/verify/{self.verify_token}/"