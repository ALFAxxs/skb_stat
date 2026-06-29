# apps/laboratory/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class LabTemplate(models.Model):
    """Laboratoriya tahlil shabloni"""
    CATEGORY_CHOICES = [
        ('general_blood', _('Umumiy qon tahlili')),
        ('biochemistry', _('Biokimyo')),
        ('urine', _('Siydik tahlili')),
        ('coagulation', _('Koagulyatsiya')),
        ('hormones', _('Gormonlar')),
        ('immunology', _('Immunologiya')),
        ('microbiology', _('Mikrobiologiya')),
        ('serology', _('Serologiya')),
        ('other', _('Boshqa')),
    ]

    name = models.CharField(max_length=255, verbose_name=_("Shablon nomi"))
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name=_("Kategoriya")
    )
    description = models.TextField(blank=True, verbose_name=_("Tavsifi"))
    is_active = models.BooleanField(default=True, verbose_name=_("Faolmi"))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name=_("Lab shabloni")
        verbose_name_plural=_("Lab shablonlari")
        ordering = ['category', 'name']


class LabParameterGroup(models.Model):
    """Parametrlar guruhi (shablon ichida)"""
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name=_("Shablon")
    )
    name = models.CharField(max_length=255, verbose_name=_("Guruh nomi"))
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Tartib raqami"))

    def __str__(self):
        return f"{self.template.name} — {self.name}"

    class Meta:
        verbose_name=_("Parametr guruhi")
        verbose_name_plural=_("Parametr guruhlari")
        ordering = ['sort_order', 'name']


class LabParameter(models.Model):
    """Laboratoriya parametri"""
    PARAM_TYPE_CHOICES = [
        ('numeric', _('Raqamli')),
        ('text', _('Matnli')),
        ('select', _('Tanlov')),
    ]

    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.CASCADE,
        related_name='parameters',
        verbose_name=_("Shablon")
    )
    group = models.ForeignKey(
        LabParameterGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='parameters',
        verbose_name=_("Guruh")
    )
    name = models.CharField(max_length=255, verbose_name=_("Nomi"))
    name_ru = models.CharField(max_length=255, blank=True, verbose_name=_("Nomi (ruscha)"))
    unit = models.CharField(max_length=50, blank=True, verbose_name=_("O'lchov birligi"))
    param_type = models.CharField(
        max_length=10,
        choices=PARAM_TYPE_CHOICES,
        default='numeric',
        verbose_name=_("Parametr turi")
    )

    # Umumiy me'yor
    normal_min = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor min")
    )
    normal_max = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor max")
    )

    # Kritik chegaralar
    critical_min = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Kritik min")
    )
    critical_max = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Kritik max")
    )

    # Erkaklar uchun me'yor
    normal_min_m = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor min (erkak)")
    )
    normal_max_m = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor max (erkak)")
    )

    # Ayollar uchun me'yor
    normal_min_f = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor min (ayol)")
    )
    normal_max_f = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name=_("Me'yor max (ayol)")
    )

    select_options = models.JSONField(
        default=list, blank=True,
        verbose_name=_("Tanlov variantlari")
    )
    is_required = models.BooleanField(default=True, verbose_name=_("Majburiy"))
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name=_("Tartib raqami"))

    def get_normal_range(self, gender=None):
        """Jinsga qarab me'yor oralig'ini qaytaradi"""
        if gender == 'M' and (self.normal_min_m is not None or self.normal_max_m is not None):
            return self.normal_min_m, self.normal_max_m
        elif gender == 'F' and (self.normal_min_f is not None or self.normal_max_f is not None):
            return self.normal_min_f, self.normal_max_f
        return self.normal_min, self.normal_max

    def get_normal_display(self, gender=None):
        """Me'yor oralig'ini matn ko'rinishida qaytaradi"""
        low, high = self.get_normal_range(gender)
        if low is not None and high is not None:
            return f"{low} – {high}"
        elif low is not None:
            return f">= {low}"
        elif high is not None:
            return f"<= {high}"
        return "—"

    def __str__(self):
        return f"{self.template.name} | {self.name}"

    class Meta:
        verbose_name=_("Lab parametri")
        verbose_name_plural=_("Lab parametrlari")
        ordering = ['sort_order', 'name']


class LabResult(models.Model):
    """Laboratoriya natijasi (to'ldirilgan shablon)"""
    STATUS_CHOICES = [
        ('draft', _('Qoralama')),
        ('done', _('Bajarildi')),
        ('verified', _('Tasdiqlandi')),
        ('printed', _('Chop etildi')),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard',
        on_delete=models.CASCADE,
        related_name='lab_results',
        verbose_name=_("Bemor kartasi")
    )
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.PROTECT,
        related_name='results',
        verbose_name=_("Shablon")
    )
    services = models.ManyToManyField(
        'services.PatientService',
        blank=True,
        related_name='lab_results',
        verbose_name=_("Xizmatlar")
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_("Holati")
    )
    conclusion = models.TextField(blank=True, verbose_name=_("Xulosa"))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_lab_results',
        verbose_name=_("Yaratgan")
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_lab_results',
        verbose_name=_("Tasdiqlagan")
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))
    printed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Chop etilgan vaqt"))

    @property
    def completion_percent(self):
        required = self.template.parameters.filter(is_required=True).count()
        if not required:
            return 100
        filled = self.values.filter(
            parameter__is_required=True
        ).exclude(value='').count()
        return int(filled / required * 100)

    @property
    def is_complete(self):
        return self.completion_percent == 100

    def __str__(self):
        return f"{self.patient_card} — {self.template.name} ({self.get_status_display()})"

    class Meta:
        verbose_name=_("Lab natijasi")
        verbose_name_plural=_("Lab natijalari")
        ordering = ['-created_at']


class LabResultValue(models.Model):
    """Laboratoriya natijasi qiymati"""
    VALUE_STATUS_CHOICES = [
        ('normal', _('Me\'yor')),
        ('high', _('Yuqori')),
        ('low', _('Past')),
        ('critical', _('Kritik')),
        ('text', _('Matnli')),
    ]

    result = models.ForeignKey(
        LabResult,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name=_("Natija")
    )
    parameter = models.ForeignKey(
        LabParameter,
        on_delete=models.CASCADE,
        related_name='result_values',
        verbose_name=_("Parametr")
    )
    value = models.CharField(max_length=500, blank=True, verbose_name=_("Qiymat"))
    value_status = models.CharField(
        max_length=10,
        choices=VALUE_STATUS_CHOICES,
        default='normal',
        verbose_name=_("Qiymat holati")
    )
    comment = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"

    class Meta:
        verbose_name=_("Natija qiymati")
        verbose_name_plural=_("Natija qiymatlari")
        unique_together = ('result', 'parameter')


# ══════════════════════════════════════════════════════
# YANGI ARXITEKTURA — ORDER SYSTEM
# ══════════════════════════════════════════════════════

class LabTemplateService(models.Model):
    """
    Service ↔ LabTemplate ko'p-ko'p bog'lanish.
    Bir xizmat bir nechta shablonga, bir shablon bir nechta xizmatga biriktirilishi mumkin.
    """
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.CASCADE,
        related_name='template_services',
        verbose_name=_("Shablon")
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='lab_template_links',
        verbose_name=_("Xizmat")
    )

    class Meta:
        unique_together = ('template', 'service')
        verbose_name=_("Shablon-Xizmat bog'lanishi")
        verbose_name_plural=_("Shablon-Xizmat bog'lanishlari")

    def __str__(self):
        return f"{self.service.name} → {self.template.name}"


class LabOrder(models.Model):
    """
    Bemor uchun laboratoriya buyurtmalar to'plami.
    Bir tashrifda berilgan barcha lab xizmatlarini birlashtiradi.
    """
    STATUS_CHOICES = [
        ('pending', _('Kutilmoqda')),
        ('partial', _('Qisman bajarildi')),
        ('completed', _('Bajarildi')),
        ('verified', _('Tasdiqlandi')),
        ('printed', _('Chop etildi')),
    ]
    patient_card = models.ForeignKey(
        'patients.PatientCard',
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name=_("Bemor")
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
        default='pending', verbose_name=_("Holat")
    )
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_lab_orders',
        verbose_name=_("Buyurtma bergan")
    )
    ordered_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Buyurtma vaqti"))
    notes = models.TextField(blank=True, verbose_name=_("Izoh"))

    def sync_status(self):
        """Barcha itemlar statusiga qarab orderni yangilash"""
        items = list(self.items.values_list('status', flat=True))
        if not items:
            return
        if all(s == 'printed' for s in items):
            new = 'printed'
        elif all(s in ('completed', 'verified', 'printed') for s in items):
            new = 'completed'
        elif any(s not in ('pending', 'rejected', 'recollect') for s in items):
            new = 'partial'
        else:
            new = 'pending'
        if self.status != new:
            self.status = new
            self.save(update_fields=['status'])

    def __str__(self):
        return f"Order #{self.pk} — {self.patient_card}"

    class Meta:
        verbose_name=_("Lab buyurtma")
        verbose_name_plural=_("Lab buyurtmalar")
        ordering = ['-ordered_at']


class LabOrderItem(models.Model):
    """
    Buyurtmadagi har bir xizmat elementi.
    Status state machine shu yerda ishlaydi.
    """
    STATUS_CHOICES = [
        ('pending', _('Kutilmoqda')),
        ('sample_taken', _('Namuna olindi')),
        ('in_progress', _('Jarayonda')),
        ('result_entering', _('Kiritilmoqda')),
        ('completed', _('Bajarildi')),
        ('verified', _('Tasdiqlandi')),
        ('printed', _('Chop etildi')),
        ('rejected', _('Rad etildi')),
        ('recollect', _('Qayta namuna kerak')),
    ]
    REJECT_REASON_CHOICES = [
        ('hemolyzed', _('Gemolizlangan namuna')),
        ('insufficient', _('Namuna yetarli emas')),
        ('wrong_tube', _('Noto\'g\'ri quvurcha')),
        ('clotted', _('Ivigan namuna')),
        ('contaminated', _('Ifloslangan namuna')),
        ('other', _('Boshqa sabab')),
    ]

    order = models.ForeignKey(
        LabOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_("Buyurtma")
    )
    patient_service = models.ForeignKey(
        'services.PatientService',
        on_delete=models.CASCADE,
        related_name='lab_order_items',
        verbose_name=_("Bemor xizmati")
    )
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items',
        verbose_name=_("Shablon")
    )
    result = models.ForeignKey(
        LabResult,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items',
        verbose_name=_("Natija")
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name=_("Holat")
    )
    reject_reason = models.CharField(
        max_length=20, choices=REJECT_REASON_CHOICES,
        blank=True, verbose_name=_("Rad sababi")
    )
    reject_note = models.TextField(blank=True, verbose_name=_("Rad izohi"))
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_lab_items',
        verbose_name=_("Mas'ul laborant")
    )
    sample_taken_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Namuna olingan vaqt")
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name=_("Bajarilgan vaqt")
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def transition(self, new_status, user, note=''):
        """
        Status o'zgartirish + avtomatik vaqt belgilash + audit log.
        Faqat ruxsat etilgan o'tishlar amalga oshiriladi.
        """
        old_status = self.status
        if old_status == new_status:
            return

        self.status = new_status
        if new_status == 'sample_taken' and not self.sample_taken_at:
            self.sample_taken_at = timezone.now()
        if new_status in ('completed', 'verified') and not self.completed_at:
            self.completed_at = timezone.now()
        if new_status == 'result_entering':
            self.assigned_to = user
        self.save()

        LabStatusLog.objects.create(
            order_item=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=user,
            note=note,
        )
        self.order.sync_status()

    def __str__(self):
        return f"{self.patient_service.service.name} [{self.get_status_display()}]"

    class Meta:
        verbose_name=_("Buyurtma elementi")
        verbose_name_plural=_("Buyurtma elementlari")
        ordering = ['created_at']


class LabStatusLog(models.Model):
    """
    Audit log — barcha status o'zgarishlari tarixi.
    O'chirilmaydi, faqat qo'shiladi.
    """
    order_item = models.ForeignKey(
        LabOrderItem,
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name=_("Buyurtma elementi")
    )
    from_status = models.CharField(max_length=20, verbose_name=_("Avvalgi holat"))
    to_status   = models.CharField(max_length=20, verbose_name=_("Yangi holat"))
    changed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("Kim o'zgartirdi")
    )
    changed_at  = models.DateTimeField(auto_now_add=True, verbose_name=_("O'zgartirilgan vaqt"))
    note        = models.TextField(blank=True, verbose_name=_("Izoh"))

    def __str__(self):
        return f"#{self.order_item_id}: {self.from_status} → {self.to_status}"

    class Meta:
        verbose_name=_("Status log")
        verbose_name_plural=_("Status loglar")
        ordering = ['changed_at']
