# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


# apps/users/models.py

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', _('Administrator')),
        ('doctor', _('Shifokor')),
        ('statistician', _('Statistik')),
        ('reception', _('Qabulxona')),
        ('laborant', _('Laborant')),
        ('nurse', _('Hamshira')),
        ('head_nurse', _('Katta hamshira')),
        ('diagnostician', _('Diagnost')),
        ('viewer', _("Faqat ko'rish")),
        ('old', 'old'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(
        'patients.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Asosiy bo'lim")
    )
    departments = models.ManyToManyField(
        'patients.Department',
        blank=True,
        related_name='staff_users',
        verbose_name=_("Bo'limlar")
    )
    phone = models.CharField(max_length=20, blank=True)

    # Shifokor kabineti uchun
    is_head = models.BooleanField(default=False, verbose_name=_("Bo'lim mudiri"))
    is_general_practitioner = models.BooleanField(
        default=False, verbose_name=_("Terapevt (barcha bemorlarga dastlabki ko'rik)")
    )

    @property
    def full_name(self):
        return self.get_full_name() or self.username

    def get_all_department_ids(self):
        """Asosiy + qo'shimcha barcha bo'lim IDlari."""
        ids = set(self.departments.values_list('pk', flat=True))
        if self.department_id:
            ids.add(self.department_id)
        return ids

    def is_admin(self):
        return self.role == 'admin'

    def is_doctor(self):
        return self.role == 'doctor'

    def is_reception(self):
        return self.role == 'reception'

    def can_edit(self):
        return self.role in ('admin', 'doctor', 'statistician', 'reception')

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"