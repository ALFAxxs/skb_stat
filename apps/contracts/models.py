# apps/contracts/models.py

import uuid
from django.db import models
from apps.patients.models import PatientCard


class Contract(models.Model):
    STATUS_CHOICES = [
        ('draft',     'Loyiha'),
        ('active',    'Faol'),
        ('cancelled', 'Bekor qilingan'),
    ]
    TYPE_CHOICES = [
        ('paid',         'Pullik'),
        ('non_resident', 'Norezident'),
    ]

    patient_card     = models.OneToOneField(
        PatientCard, on_delete=models.CASCADE,
        related_name='contract', verbose_name="Bemor kartasi"
    )
    contract_number  = models.CharField(max_length=30, unique=True, verbose_name="Shartnoma raqami")
    contract_date    = models.DateField(auto_now_add=True, verbose_name="Shartnoma sanasi")
    contract_type    = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Turi")
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES,
                                        default='active', verbose_name="Holati")
    verify_token     = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    pdf_file         = models.FileField(upload_to='contracts/', blank=True, null=True,
                                        verbose_name="PDF fayl")
    created_at       = models.DateTimeField(auto_now_add=True)
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shartnoma"
        verbose_name_plural = "Shartnomalar"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.contract_number} — {self.patient_card.full_name}"

    @property
    def verify_url(self):
        return f"/contracts/verify/{self.verify_token}/"