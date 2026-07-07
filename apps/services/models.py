# apps/services/models.py

from django.db import models
from django.db.models import Sum
from django.utils import translation
from django.utils.translation import gettext_lazy as _
from apps.patients.models import PatientCard, Department


class ServiceCategory(models.Model):
    """Xizmat kategoriyalari"""
    CATEGORY_TYPE_CHOICES = [
        ('lab', _('Laboratoriya')),
        ('radiology', _('Rentgen/UZI/MRT')),
        ('surgery', _('Jarrohlik')),
        ('physio', _('Fizioterapiya')),
        ('consultation', _('Konsultatsiya')),
        ('other', _('Boshqa')),
    ]
    name    = models.CharField(max_length=100, verbose_name=_("Nomi"))
    name_ru = models.CharField(max_length=100, blank=True, verbose_name=_("Nomi (ruscha)"))
    code    = models.CharField(max_length=20, blank=True, verbose_name=_("Kodi"))
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPE_CHOICES,
        default='other',
        verbose_name=_("Turi")
    )
    icon = models.CharField(
        max_length=10, blank=True, default='🏥',
        verbose_name=_("Ikona (emoji)")
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def display_name(self):
        if translation.get_language() == 'ru' and self.name_ru:
            return self.name_ru
        return self.name

    class Meta:
        verbose_name = _("Xizmat kategoriyasi")
        verbose_name_plural = _("Xizmat kategoriyalari")
        ordering = ['category_type', 'name']


class Service(models.Model):
    """Xizmat turlari"""
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.CASCADE,
        related_name='services',
        verbose_name=_("Kategoriya")
    )
    name    = models.CharField(max_length=255, verbose_name=_("Xizmat nomi"))
    name_ru = models.CharField(max_length=255, blank=True, verbose_name=_("Nomi (ruscha)"))
    code    = models.CharField(max_length=20, blank=True, verbose_name=_("Kodi"))
    description = models.TextField(blank=True, verbose_name=_("Tavsifi"))

    # 3 xil narx
    price_normal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Oddiy narx (so'm)")
    )
    price_railway = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name=_("Temir yo'lchi narxi (so'm)")
    )
    # Norezident narxi = oddiy narx * 1.25 (avtomatik hisoblanadi)

    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Mas'ul bo'lim")
    )
    lab_template = models.ForeignKey(
        'laboratory.LabTemplate',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='linked_services',
        verbose_name=_("Lab shabloni")
    )
    is_active    = models.BooleanField(default=True)
    is_operation = models.BooleanField(default=False, verbose_name=_("Operatsiyami?"))
    non_resident_surcharge = models.BooleanField(
        default=True,
        verbose_name=_("Norezident +25%"),
        help_text=_("Yoqilsa — norezident uchun narx avtomatik 25% qimmatroq hisoblanadi.")
    )

    # Konsultatsiya turidagi xizmatlar uchun — ushbu xizmatni qaysi shifokor(lar) ko'ra oladi
    assigned_doctors = models.ManyToManyField(
        'users.CustomUser', blank=True, related_name='assignable_services',
        verbose_name=_("Biriktirilgan shifokorlar")
    )

    def price_for_patient(self, patient_category):
        """Bemor kategoriyasiga qarab narx hisoblash"""
        from decimal import Decimal
        if patient_category == 'railway':
            return self.price_railway if self.price_railway else self.price_normal
        elif patient_category == 'non_resident' and self.non_resident_surcharge:
            base = self.price_normal if self.price_normal else self.price_railway
            return round(base * Decimal('1.25'), 2)
        else:
            return self.price_normal

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name

    @property
    def display_name(self):
        if translation.get_language() == 'ru' and self.name_ru:
            return self.name_ru
        return self.name

    class Meta:
        verbose_name = _("Xizmat")
        verbose_name_plural = _("Xizmatlar")
        ordering = ['category', 'name']


class PatientService(models.Model):
    """Bemorga biriktirilgan xizmat"""
    STATUS_CHOICES = [
        ('ordered',     _('Buyurtma berildi')),
        ('in_progress', _('Bajarilmoqda')),
        ('completed',   _('Bajarildi')),
        ('cancelled',   _('Bekor qilindi')),
    ]

    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='patient_services',
        verbose_name=_("Bemor kartasi")
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        verbose_name=_("Xizmat")
    )
    quantity = models.PositiveIntegerField(default=1, verbose_name=_("Miqdori"))
    status   = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
        default='ordered', verbose_name=_("Holati")
    )

    # Buyurtma beruvchi
    ordered_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordered_services',
        verbose_name=_("Buyurtma bergan shifokor")
    )
    ordered_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Buyurtma sanasi"))

    # Bajargchi
    performed_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='performed_services',
        verbose_name=_("Bajargan shifokor")
    )
    performed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Bajarilgan sana"))

    # Natija
    result = models.TextField(blank=True, verbose_name=_("Natija / Xulosa"))

    # Narx
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name=_("Birlik narxi (so'm)")
    )
    patient_category_at_order = models.CharField(
        max_length=15, blank=True,
        verbose_name=_("Buyurtma paytidagi bemor kategoriyasi")
    )

    is_paid = models.BooleanField(default=False, verbose_name=_("To'langan"))
    notes   = models.TextField(blank=True, verbose_name=_("Izoh"))

    @property
    def total_price(self):
        return self.price * self.quantity

    def save(self, *args, **kwargs):
        if not self.pk and self.service_id and self.patient_card_id:
            category = self.patient_card.patient_category
            self.patient_category_at_order = category
            self.price = self.service.price_for_patient(category)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.patient_card} — {self.service.name}"

    class Meta:
        verbose_name = _("Bemor xizmati")
        verbose_name_plural = _("Bemor xizmatlari")
        ordering = ['-ordered_at']


# ==================== DORI-DARMON ====================

class Medicine(models.Model):
    """Dori-darmon katalogi"""
    UNIT_CHOICES = [
        ('dona',     _('dona')),
        ('ml',       _('ml')),
        ('mg',       _('mg')),
        ('g',        _('g')),
        ('l',        _('l')),
        ('ampula',   _('ampula')),
        ('kapsula',  _('kapsula')),
        ('tabletka', _('tabletka')),
        ('paket',    _('paket')),
        ('shisha',   _('shisha')),
        ('tuba',     _('tuba')),
    ]
    DOSAGE_FORM_CHOICES = [
        ('tabletka',    _('Tabletka')),
        ('kapsula',     _('Kapsula')),
        ('eritma',      _('Eritma (inyeksiya uchun)')),
        ('sirop',       _('Sirop')),
        ('tomchi',      _('Tomchi')),
        ('malham',      _('Malham')),
        ('krem',        _('Krem')),
        ('kukun',       _('Kukun')),
        ('suspenziya',  _('Suspenziya')),
        ('aerozol',     _('Aerozol')),
        ('gel',         _('Gel')),
        ('sham',        _('Sham (suppozitoriy)')),
        ('patch',       _('Patch (yopishtirgich)')),
        ('other',       _('Boshqa')),
    ]
    CATEGORY_CHOICES = [
        ('drug',  _('Dori')),
        ('lab',   _('Laboratoriya anjomi')),
        ('other', _('Boshqa')),
    ]

    name         = models.CharField(max_length=255, verbose_name=_("Savdo nomi"))
    mnn          = models.CharField(max_length=255, blank=True, verbose_name=_("МНН (xalqaro nomi)"), db_index=True)
    dosage_form  = models.CharField(max_length=20, choices=DOSAGE_FORM_CHOICES, blank=True, verbose_name=_("Chiqarish shakli"))
    strength     = models.CharField(max_length=100, blank=True, verbose_name=_("Doza / konsentratsiya"))
    unit         = models.CharField(max_length=20, choices=UNIT_CHOICES, default='dona', verbose_name=_("Birlik"))
    category     = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='drug', verbose_name=_("Kategoriya"))
    is_active    = models.BooleanField(default=True)

    def __str__(self):
        parts = [self.name]
        if self.strength:
            parts.append(self.strength)
        if self.dosage_form:
            parts.append(self.get_dosage_form_display())
        return ' — '.join(parts)

    class Meta:
        verbose_name = _("Dori-darmon")
        verbose_name_plural = _("Dori-darmonlar")
        ordering = ['name']


class PatientMedicine(models.Model):
    """Bemorga biriktirilgan dori"""
    SOURCE_CHOICES = [
        ('hospital', _("Bo'lim dorixonasi")),
        ('patient',  _("Bemor o'zi olib keldi")),
    ]

    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='patient_medicines',
        verbose_name=_("Bemor kartasi")
    )
    medicine = models.ForeignKey(
        Medicine,
        on_delete=models.PROTECT,
        verbose_name=_("Dori")
    )
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=1, verbose_name=_("Miqdori")
    )
    price = models.DecimalField(
        max_digits=12, decimal_places=2,
        default=0, verbose_name=_("Narxi (so'm)")
    )
    ordered_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='ordered_medicines',
        verbose_name=_("Buyurtma bergan shifokor")
    )
    ordered_at = models.DateTimeField(auto_now_add=True)
    notes      = models.TextField(blank=True, verbose_name=_("Izoh"))
    source     = models.CharField(
        max_length=10, choices=SOURCE_CHOICES,
        default='hospital', verbose_name=_("Manba")
    )

    @property
    def total_price(self):
        from decimal import Decimal
        if self.source == 'patient':
            return Decimal('0')
        return self.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.patient_card} — {self.medicine.name}"

    class Meta:
        verbose_name = _("Bemor dorisi")
        verbose_name_plural = _("Bemor dorilari")
        ordering = ['-ordered_at']


# apps/services/models.py ga qo'shish — oxiriga

class ServicePackage(models.Model):
    """Shifokor xizmat paketi"""
    name        = models.CharField(max_length=200, verbose_name=_("Paket nomi"))
    owner       = models.ForeignKey(
        'users.CustomUser', on_delete=models.CASCADE,
        related_name='service_packages', verbose_name=_("Shifokor")
    )
    services    = models.ManyToManyField(
        'Service', through='ServicePackageItem',
        related_name='packages', verbose_name=_("Xizmatlar")
    )
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Xizmat paketi")
        verbose_name_plural = _("Xizmat paketlari")
        ordering            = ['name']

    def __str__(self):
        return f"{self.name} ({self.owner})"


class ServicePackageItem(models.Model):
    """Paket tarkibidagi xizmat"""
    package    = models.ForeignKey(ServicePackage, on_delete=models.CASCADE, related_name='items')
    service    = models.ForeignKey('Service', on_delete=models.CASCADE)
    quantity   = models.PositiveSmallIntegerField(default=1)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'service__name']
        unique_together = ('package', 'service')