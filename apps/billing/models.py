# apps/billing/models.py

from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.patients.models import PatientCard


class Invoice(models.Model):
    """Bemorning yagona hisob-faktura yozuvi (har bir yotqizilish uchun bitta)"""
    STATUS_CHOICES = [
        ('unpaid',    _("To'lanmagan")),
        ('partial',   _("Qisman to'langan")),
        ('paid',      _("To'liq to'langan")),
        ('cancelled', _("Bekor qilingan")),
    ]

    patient_card = models.OneToOneField(
        PatientCard, on_delete=models.CASCADE,
        related_name='invoice', verbose_name=_("Bemor kartasi")
    )
    invoice_number = models.CharField(max_length=30, unique=True, verbose_name=_("Hisob-faktura raqami"))
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='unpaid', verbose_name=_("Holati"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.invoice_number

    class Meta:
        verbose_name = _("Hisob-faktura")
        verbose_name_plural = _("Hisob-fakturalar")
        ordering = ['-created_at']


class Payment(models.Model):
    """Hisob-fakturaga qarshi qabul qilingan to'lov"""
    METHOD_CHOICES = [
        ('cash',          _('Naqd')),
        ('card',          _('Plastik karta')),
        ('bank_transfer', _("Bank o'tkazmasi")),
        ('insurance',     _("Sug'urta")),
    ]

    invoice    = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments', verbose_name=_("Hisob-faktura"))
    amount     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Summa (so'm)"))
    method     = models.CharField(max_length=15, choices=METHOD_CHOICES, default='cash', verbose_name=_("To'lov usuli"))
    cashier    = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_("Kassir"))
    comment    = models.CharField(max_length=255, blank=True, verbose_name=_("Izoh"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice} — {self.amount} so'm"

    class Meta:
        verbose_name = _("To'lov")
        verbose_name_plural = _("To'lovlar")
        ordering = ['-created_at']


class Discount(models.Model):
    """Hisob-fakturaga qo'llanilgan chegirma"""
    invoice    = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='discounts', verbose_name=_("Hisob-faktura"))
    amount     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Chegirma summasi (so'm)"))
    reason     = models.CharField(max_length=255, blank=True, verbose_name=_("Sababi"))
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_("Kim qo'shdi"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice} — chegirma {self.amount} so'm"

    class Meta:
        verbose_name = _("Chegirma")
        verbose_name_plural = _("Chegirmalar")
        ordering = ['-created_at']


class Refund(models.Model):
    """Bemorga qaytarilgan summa"""
    invoice    = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='refunds', verbose_name=_("Hisob-faktura"))
    amount     = models.DecimalField(max_digits=12, decimal_places=2, verbose_name=_("Qaytarilgan summa (so'm)"))
    reason     = models.CharField(max_length=255, blank=True, verbose_name=_("Sababi"))
    created_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_("Kim qaytardi"))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice} — qaytarish {self.amount} so'm"

    class Meta:
        verbose_name = _("Qaytarish (Refund)")
        verbose_name_plural = _("Qaytarishlar (Refundlar)")
        ordering = ['-created_at']


class Consumable(models.Model):
    """Sarflanadigan materiallar katalogi"""
    name      = models.CharField(max_length=255, verbose_name=_("Nomi"))
    unit      = models.CharField(max_length=20, default='dona', verbose_name=_("Birlik"))
    price     = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Narxi (so'm)"))
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Sarflanadigan material")
        verbose_name_plural = _("Sarflanadigan materiallar")
        ordering = ['name']


class PatientConsumable(models.Model):
    """Bemorga sarflangan material"""
    patient_card = models.ForeignKey(
        PatientCard, on_delete=models.CASCADE,
        related_name='patient_consumables', verbose_name=_("Bemor kartasi")
    )
    consumable = models.ForeignKey(Consumable, on_delete=models.PROTECT, verbose_name=_("Material"))
    quantity   = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name=_("Miqdori"))
    price      = models.DecimalField(max_digits=12, decimal_places=2, default=0, verbose_name=_("Narxi (so'm)"))
    ordered_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='+', verbose_name=_("Kim qo'shdi")
    )
    ordered_at = models.DateTimeField(auto_now_add=True)
    notes      = models.TextField(blank=True, verbose_name=_("Izoh"))

    @property
    def total_price(self):
        return self.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.patient_card} — {self.consumable.name}"

    class Meta:
        verbose_name = _("Bemorga sarflangan material")
        verbose_name_plural = _("Bemorga sarflangan materiallar")
        ordering = ['-ordered_at']


class BillingAuditLog(models.Model):
    """Hisob-faktura bo'yicha amallar jurnali"""
    ACTION_CHOICES = [
        ('invoice_created', _("Hisob-faktura yaratildi")),
        ('payment_added',   _("To'lov qo'shildi")),
        ('discount_added',  _("Chegirma qo'shildi")),
        ('refund_added',    _("Qaytarish qo'shildi")),
        ('consumable_added', _("Material qo'shildi")),
        ('recalculated',    _("Qayta hisoblandi")),
        ('status_changed',  _("Holati o'zgardi")),
    ]

    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='audit_logs', verbose_name=_("Hisob-faktura"))
    actor       = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='+', verbose_name=_("Kim bajardi"))
    action      = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_("Amal"))
    description = models.CharField(max_length=500, blank=True, verbose_name=_("Tavsif"))
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.invoice} — {self.get_action_display()}"

    class Meta:
        verbose_name = _("Audit yozuvi")
        verbose_name_plural = _("Audit jurnali")
        ordering = ['-created_at']
