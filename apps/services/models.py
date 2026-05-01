# apps/services/models.py

from django.db import models
from django.db.models import Sum
from apps.patients.models import PatientCard, Department, Doctor


class ServiceCategory(models.Model):
    """Xizmat kategoriyalari"""
    CATEGORY_TYPE_CHOICES = [
        ('lab', 'Laboratoriya'),
        ('radiology', 'Rentgen/UZI/MRT'),
        ('surgery', 'Jarrohlik'),
        ('physio', 'Fizioterapiya'),
        ('consultation', 'Konsultatsiya'),
        ('other', 'Boshqa'),
    ]
    name = models.CharField(max_length=100, verbose_name="Nomi")
    code = models.CharField(max_length=20, blank=True, verbose_name="Kodi")
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPE_CHOICES,
        default='other',
        verbose_name="Turi"
    )
    icon = models.CharField(
        max_length=10, blank=True, default='🏥',
        verbose_name="Ikona (emoji)"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Xizmat kategoriyasi"
        verbose_name_plural = "Xizmat kategoriyalari"
        ordering = ['category_type', 'name']


class Service(models.Model):
    """Xizmat turlari"""
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name="Kategoriya"
    )
    name = models.CharField(max_length=255, verbose_name="Xizmat nomi")
    code = models.CharField(max_length=20, blank=True, verbose_name="Kodi")
    description = models.TextField(blank=True, verbose_name="Tavsifi")

    # 3 xil narx
    price_normal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Oddiy narx (so'm)"
    )
    price_railway = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name="Temir yo'lchi narxi (so'm)"
    )
    # Norezident narxi = oddiy narx * 1.25 (avtomatik hisoblanadi)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Mas'ul bo'lim"
    )
    is_active = models.BooleanField(default=True)
    is_operation = models.BooleanField(
        default=False,
        verbose_name="Operatsiyami?"
    )

    def price_for_patient(self, patient_category):
        """Bemor kategoriyasiga qarab narx hisoblash"""
        from decimal import Decimal
        if patient_category == 'railway':
            return self.price_railway if self.price_railway else self.price_normal
        elif patient_category == 'non_resident':
            return round(self.price_normal * Decimal('1.25'), 2)
        else:
            return self.price_normal

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name

    class Meta:
        verbose_name = "Xizmat"
        verbose_name_plural = "Xizmatlar"
        ordering = ['category', 'name']


class PatientService(models.Model):
    """Bemorga biriktirilgan xizmat"""
    STATUS_CHOICES = [
        ('ordered', 'Buyurtma berildi'),
        ('in_progress', 'Bajarilmoqda'),
        ('completed', 'Bajarildi'),
        ('cancelled', 'Bekor qilindi'),
    ]

    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='patient_services',
        verbose_name="Bemor kartasi"
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        verbose_name="Xizmat"
    )
    quantity = models.PositiveIntegerField(
        default=1,
        verbose_name="Miqdori"
    )
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='ordered',
        verbose_name="Holati"
    )

    # Buyurtma beruvchi
    ordered_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordered_services',
        verbose_name="Buyurtma bergan shifokor"
    )
    ordered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Buyurtma sanasi"
    )

    # Bajargchi
    performed_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='performed_services',
        verbose_name="Bajargan shifokor"
    )
    performed_at = models.DateTimeField(
        null=True, blank=True,
        verbose_name="Bajarilgan sana"
    )

    # Natija
    result = models.TextField(blank=True, verbose_name="Natija / Xulosa")

    # Narx
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0,
        verbose_name="Birlik narxi (so'm)"
    )
    # Bemor kategoriyasi saqlash
    patient_category_at_order = models.CharField(
        max_length=15, blank=True,
        verbose_name="Buyurtma paytidagi bemor kategoriyasi"
    )

    is_paid = models.BooleanField(default=False, verbose_name="To'langan")
    notes = models.TextField(blank=True, verbose_name="Izoh")

    @property
    def total_price(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        # Narxni avtomatik hisoblash
        if not self.pk and self.service_id and self.patient_card_id:
            category = self.patient_card.patient_category
            self.patient_category_at_order = category
            self.price = self.service.price_for_patient(category)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_card} — {self.service.name}"

    class Meta:
        verbose_name = "Bemor xizmati"
        verbose_name_plural = "Bemor xizmatlari"
        ordering = ['-ordered_at']

# ==================== DORI-DARMON ====================

class Medicine(models.Model):
    """Dori-darmon katalogi"""
    UNIT_CHOICES = [
        ('dona', 'dona'),
        ('ml', 'ml'),
        ('mg', 'mg'),
        ('g', 'g'),
        ('l', 'l'),
        ('ampula', 'ampula'),
        ('kapsula', 'kapsula'),
        ('tabletka', 'tabletka'),
        ('paket', 'paket'),
        ('shisha', 'shisha'),
        ('tuba', 'tuba'),
    ]
    name = models.CharField(max_length=255, verbose_name="Nomi")
    unit = models.CharField(
        max_length=20, choices=UNIT_CHOICES,
        default='dona', verbose_name="Birlik"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.unit})"

    class Meta:
        verbose_name = "Dori-darmon"
        verbose_name_plural = "Dori-darmonlar"
        ordering = ['name']


class PatientMedicine(models.Model):
    """Bemorga biriktirilgan dori"""
    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='patient_medicines',
        verbose_name="Bemor kartasi"
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        verbose_name="Dori"
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=1, verbose_name="Miqdori"
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name="Narxi (so'm)"
    )
    ordered_by = models.ForeignKey(
        Doctor,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordered_medicines',
        verbose_name="Buyurtma bergan shifokor"
    )
    ordered_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, verbose_name="Izoh")

    @property
    def total_price(self):
        from decimal import Decimal
        return self.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.patient_card} — {self.medicine.name}"

    class Meta:
        verbose_name = "Bemor dorisi"
        verbose_name_plural = "Bemor dorilari"
        ordering = ['-ordered_at']
