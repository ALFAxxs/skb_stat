# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


# apps/users/models.py

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('doctor', 'Shifokor'),
        ('statistician', 'Statistik'),
        ('reception', 'Qabulxona'),
        ('laborant', 'Laborant'),
        ('viewer', "Faqat ko'rish"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(
        'patients.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Asosiy bo'lim"
    )
    departments = models.ManyToManyField(
        'patients.Department',
        blank=True,
        related_name='staff_users',
        verbose_name="Bo'limlar"
    )
    phone = models.CharField(max_length=20, blank=True)

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