# apps/users/models.py

from django.contrib.auth.models import AbstractUser
from django.db import models


# apps/users/models.py

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('doctor', 'Shifokor'),
        ('statistician', 'Statistik'),
        ('reception', 'Qabulxona'),      # ← qo'shildi
        ('viewer', "Faqat ko'rish"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='viewer')
    department = models.ForeignKey(
        'patients.Department',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    phone = models.CharField(max_length=20, blank=True)

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