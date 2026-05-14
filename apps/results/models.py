# apps/results/models.py

from django.db import models
from django.utils import timezone


class ResultTemplate(models.Model):
    """Natija shablonlari — admin tomonidan yaratiladi"""

    CATEGORY_CHOICES = [
        ('lab',          '🔬 Laboratoriya'),
        ('radiology',    '🩻 Rentgen / UZI / MRT'),
        ('consultation', '👨‍⚕️ Konsultatsiya'),
        ('procedure',    '💉 Muolaja'),
        ('other',        '📄 Boshqa'),
    ]

    name        = models.CharField(max_length=200, verbose_name="Shablon nomi")
    category    = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES,
        default='other', verbose_name="Kategoriya"
    )
    content     = models.TextField(verbose_name="Shablon HTML kontent")
    description = models.CharField(max_length=300, blank=True, verbose_name="Tavsif")
    is_active   = models.BooleanField(default=True, verbose_name="Faol")
    created_by  = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name="Yaratuvchi"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Natija shabloni"
        verbose_name_plural = "Natija shablonlari"
        ordering            = ['category', 'name']

    def __str__(self):
        return f"{self.get_category_display()} — {self.name}"


class ServiceResult(models.Model):
    """Xizmat natijasi / javob"""

    STATUS_CHOICES = [
        ('draft',     '✏️ Qoralama'),
        ('completed', '✅ Yakunlangan'),
    ]

    patient_service = models.OneToOneField(
        'services.PatientService',
        on_delete=models.CASCADE,
        related_name='result',
        verbose_name="Xizmat"
    )
    template        = models.ForeignKey(
        ResultTemplate, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Shablon"
    )
    content         = models.TextField(verbose_name="Natija HTML kontent")
    status          = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='draft', verbose_name="Holat"
    )
    created_by      = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='results_created',
        verbose_name="Kim kiritdi"
    )
    updated_by      = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='results_updated',
        verbose_name="Kim tahrirladi"
    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Xizmat natijasi"
        verbose_name_plural = "Xizmat natijalari"
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.patient_service} — {self.get_status_display()}"

    @property
    def patient(self):
        return self.patient_service.patient_card
