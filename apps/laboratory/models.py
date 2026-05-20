# apps/laboratory/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone


class LabTemplate(models.Model):
    """Laboratoriya tahlil shabloni"""
    CATEGORY_CHOICES = [
        ('general_blood', 'Umumiy qon tahlili'),
        ('biochemistry', 'Biokimyo'),
        ('urine', 'Siydik tahlili'),
        ('coagulation', 'Koagulyatsiya'),
        ('hormones', 'Gormonlar'),
        ('immunology', 'Immunologiya'),
        ('microbiology', 'Mikrobiologiya'),
        ('serology', 'Serologiya'),
        ('other', 'Boshqa'),
    ]

    name = models.CharField(max_length=255, verbose_name="Shablon nomi")
    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default='other',
        verbose_name="Kategoriya"
    )
    description = models.TextField(blank=True, verbose_name="Tavsifi")
    is_active = models.BooleanField(default=True, verbose_name="Faolmi")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Lab shabloni"
        verbose_name_plural = "Lab shablonlari"
        ordering = ['category', 'name']


class LabParameterGroup(models.Model):
    """Parametrlar guruhi (shablon ichida)"""
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name="Shablon"
    )
    name = models.CharField(max_length=255, verbose_name="Guruh nomi")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="Tartib raqami")

    def __str__(self):
        return f"{self.template.name} — {self.name}"

    class Meta:
        verbose_name = "Parametr guruhi"
        verbose_name_plural = "Parametr guruhlari"
        ordering = ['sort_order', 'name']


class LabParameter(models.Model):
    """Laboratoriya parametri"""
    PARAM_TYPE_CHOICES = [
        ('numeric', 'Raqamli'),
        ('text', 'Matnli'),
        ('select', 'Tanlov'),
    ]

    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.CASCADE,
        related_name='parameters',
        verbose_name="Shablon"
    )
    group = models.ForeignKey(
        LabParameterGroup,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='parameters',
        verbose_name="Guruh"
    )
    name = models.CharField(max_length=255, verbose_name="Nomi")
    name_ru = models.CharField(max_length=255, blank=True, verbose_name="Nomi (ruscha)")
    unit = models.CharField(max_length=50, blank=True, verbose_name="O'lchov birligi")
    param_type = models.CharField(
        max_length=10,
        choices=PARAM_TYPE_CHOICES,
        default='numeric',
        verbose_name="Parametr turi"
    )

    # Umumiy me'yor
    normal_min = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor min"
    )
    normal_max = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor max"
    )

    # Kritik chegaralar
    critical_min = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Kritik min"
    )
    critical_max = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Kritik max"
    )

    # Erkaklar uchun me'yor
    normal_min_m = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor min (erkak)"
    )
    normal_max_m = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor max (erkak)"
    )

    # Ayollar uchun me'yor
    normal_min_f = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor min (ayol)"
    )
    normal_max_f = models.DecimalField(
        max_digits=10, decimal_places=4,
        null=True, blank=True,
        verbose_name="Me'yor max (ayol)"
    )

    select_options = models.JSONField(
        default=list, blank=True,
        verbose_name="Tanlov variantlari"
    )
    is_required = models.BooleanField(default=True, verbose_name="Majburiy")
    sort_order = models.PositiveSmallIntegerField(default=0, verbose_name="Tartib raqami")

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
        verbose_name = "Lab parametri"
        verbose_name_plural = "Lab parametrlari"
        ordering = ['sort_order', 'name']


class LabResult(models.Model):
    """Laboratoriya natijasi (to'ldirilgan shablon)"""
    STATUS_CHOICES = [
        ('draft',     'Qoralama'),
        ('done',      'Bajarildi'),
        ('verified',  'Tasdiqlandi'),
        ('printed',   'Chop etildi'),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard',
        on_delete=models.CASCADE,
        related_name='lab_results',
        verbose_name="Bemor kartasi"
    )
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.PROTECT,
        related_name='results',
        verbose_name="Shablon"
    )
    services = models.ManyToManyField(
        'services.PatientService',
        blank=True,
        related_name='lab_results',
        verbose_name="Xizmatlar"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Holati"
    )
    conclusion = models.TextField(blank=True, verbose_name="Xulosa")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_lab_results',
        verbose_name="Yaratgan"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='verified_lab_results',
        verbose_name="Tasdiqlagan"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")
    printed_at = models.DateTimeField(null=True, blank=True, verbose_name="Chop etilgan vaqt")

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
        verbose_name = "Lab natijasi"
        verbose_name_plural = "Lab natijalari"
        ordering = ['-created_at']


class LabResultValue(models.Model):
    """Laboratoriya natijasi qiymati"""
    VALUE_STATUS_CHOICES = [
        ('normal', 'Me\'yor'),
        ('high', 'Yuqori'),
        ('low', 'Past'),
        ('critical', 'Kritik'),
        ('text', 'Matnli'),
    ]

    result = models.ForeignKey(
        LabResult,
        on_delete=models.CASCADE,
        related_name='values',
        verbose_name="Natija"
    )
    parameter = models.ForeignKey(
        LabParameter,
        on_delete=models.CASCADE,
        related_name='result_values',
        verbose_name="Parametr"
    )
    value = models.CharField(max_length=500, blank=True, verbose_name="Qiymat")
    value_status = models.CharField(
        max_length=10,
        choices=VALUE_STATUS_CHOICES,
        default='normal',
        verbose_name="Qiymat holati"
    )
    comment = models.CharField(max_length=500, blank=True, verbose_name="Izoh")

    def __str__(self):
        return f"{self.parameter.name}: {self.value}"

    class Meta:
        verbose_name = "Natija qiymati"
        verbose_name_plural = "Natija qiymatlari"
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
        verbose_name="Shablon"
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='lab_template_links',
        verbose_name="Xizmat"
    )

    class Meta:
        unique_together = ('template', 'service')
        verbose_name = "Shablon-Xizmat bog'lanishi"
        verbose_name_plural = "Shablon-Xizmat bog'lanishlari"

    def __str__(self):
        return f"{self.service.name} → {self.template.name}"


class LabOrder(models.Model):
    """
    Bemor uchun laboratoriya buyurtmalar to'plami.
    Bir tashrifda berilgan barcha lab xizmatlarini birlashtiradi.
    """
    STATUS_CHOICES = [
        ('pending',   'Kutilmoqda'),
        ('partial',   'Qisman bajarildi'),
        ('completed', 'Bajarildi'),
        ('verified',  'Tasdiqlandi'),
        ('printed',   'Chop etildi'),
    ]
    patient_card = models.ForeignKey(
        'patients.PatientCard',
        on_delete=models.CASCADE,
        related_name='lab_orders',
        verbose_name="Bemor"
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES,
        default='pending', verbose_name="Holat"
    )
    ordered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_lab_orders',
        verbose_name="Buyurtma bergan"
    )
    ordered_at = models.DateTimeField(auto_now_add=True, verbose_name="Buyurtma vaqti")
    notes = models.TextField(blank=True, verbose_name="Izoh")

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
        verbose_name = "Lab buyurtma"
        verbose_name_plural = "Lab buyurtmalar"
        ordering = ['-ordered_at']


class LabOrderItem(models.Model):
    """
    Buyurtmadagi har bir xizmat elementi.
    Status state machine shu yerda ishlaydi.
    """
    STATUS_CHOICES = [
        ('pending',         'Kutilmoqda'),
        ('sample_taken',    'Namuna olindi'),
        ('in_progress',     'Jarayonda'),
        ('result_entering', 'Kiritilmoqda'),
        ('completed',       'Bajarildi'),
        ('verified',        'Tasdiqlandi'),
        ('printed',         'Chop etildi'),
        ('rejected',        'Rad etildi'),
        ('recollect',       'Qayta namuna kerak'),
    ]
    REJECT_REASON_CHOICES = [
        ('hemolyzed',    'Gemolizlangan namuna'),
        ('insufficient', 'Namuna yetarli emas'),
        ('wrong_tube',   'Noto\'g\'ri quvurcha'),
        ('clotted',      'Ivigan namuna'),
        ('contaminated', 'Ifloslangan namuna'),
        ('other',        'Boshqa sabab'),
    ]

    order = models.ForeignKey(
        LabOrder,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name="Buyurtma"
    )
    patient_service = models.ForeignKey(
        'services.PatientService',
        on_delete=models.CASCADE,
        related_name='lab_order_items',
        verbose_name="Bemor xizmati"
    )
    template = models.ForeignKey(
        LabTemplate,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items',
        verbose_name="Shablon"
    )
    result = models.ForeignKey(
        LabResult,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='order_items',
        verbose_name="Natija"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES,
        default='pending', verbose_name="Holat"
    )
    reject_reason = models.CharField(
        max_length=20, choices=REJECT_REASON_CHOICES,
        blank=True, verbose_name="Rad sababi"
    )
    reject_note = models.TextField(blank=True, verbose_name="Rad izohi")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='assigned_lab_items',
        verbose_name="Mas'ul laborant"
    )
    sample_taken_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Namuna olingan vaqt"
    )
    completed_at = models.DateTimeField(
        null=True, blank=True, verbose_name="Bajarilgan vaqt"
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
        verbose_name = "Buyurtma elementi"
        verbose_name_plural = "Buyurtma elementlari"
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
        verbose_name="Buyurtma elementi"
    )
    from_status = models.CharField(max_length=20, verbose_name="Avvalgi holat")
    to_status   = models.CharField(max_length=20, verbose_name="Yangi holat")
    changed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Kim o'zgartirdi"
    )
    changed_at  = models.DateTimeField(auto_now_add=True, verbose_name="O'zgartirilgan vaqt")
    note        = models.TextField(blank=True, verbose_name="Izoh")

    def __str__(self):
        return f"#{self.order_item_id}: {self.from_status} → {self.to_status}"

    class Meta:
        verbose_name = "Status log"
        verbose_name_plural = "Status loglar"
        ordering = ['changed_at']
