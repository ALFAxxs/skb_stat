# apps/care/models.py

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ==================== YO'LLANMA (REFERRAL) ====================

class Referral(models.Model):
    SERVICE_TYPE_CHOICES = [
        ('consultation', _('Konsultatsiya')),
        ('diagnostic', _('Diagnostik tekshiruv')),
        ('lab', _('Laboratoriya tekshiruvi')),
        ('treatment', _('Muolaja')),
        ('other', _('Boshqa xizmatlar')),
    ]
    PRIORITY_CHOICES = [
        ('normal', _('Oddiy')),
        ('urgent', _('Shoshilinch')),
        ('critical', _('Juda shoshilinch')),
    ]
    STATUS_CHOICES = [
        ('sent', _('Yuborildi')),
        ('in_progress', _('Bajarilmoqda')),
        ('done', _('Bajarildi')),
        ('cancelled', _('Bekor qilindi')),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='referrals', verbose_name=_("Bemor kartasi")
    )
    referring_doctor = models.ForeignKey(
        'patients.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sent_referrals',
        verbose_name=_("Yo'llanma bergan shifokor")
    )
    target_doctor = models.ForeignKey(
        'patients.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='received_referrals',
        verbose_name=_("Tanlangan shifokor")
    )

    service_type = models.CharField(
        max_length=20, choices=SERVICE_TYPE_CHOICES, verbose_name=_("Xizmat turi")
    )
    service_detail = models.CharField(
        max_length=255, blank=True, verbose_name=_("Xizmat tafsiloti")
    )
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal',
        verbose_name=_("Ustuvorlik")
    )
    scheduled_at = models.DateTimeField(verbose_name=_("Qabul sanasi va vaqti"))
    comment = models.TextField(blank=True, verbose_name=_("Izoh"))
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='sent', verbose_name=_("Holati")
    )

    # Avtomatik yaratilgan bog'liq yozuv (ConsultationRequest / DiagnosticAssignment /
    # LabTestAssignment / TreatmentProcedure)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    linked_object = GenericForeignKey('content_type', 'object_id')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_referrals',
        verbose_name=_("Yaratgan foydalanuvchi")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name=_("Yo'llanma")
        verbose_name_plural=_("Yo'llanmalar")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.get_service_type_display()} — {self.patient_card} ({self.get_priority_display()})"


# ==================== DORI/MUOLAJA TAYINLASH ====================

class MedicationOrder(models.Model):
    MEDICINE_TYPE_CHOICES = [
        ('tablet', _('Tabletka')),
        ('capsule', _('Kapsula')),
        ('injection', _('Ukol')),
        ('drops', _('Tomchi')),
        ('ointment', _('Maz')),
        ('system', _('Sistema')),
        ('other', _('Boshqa')),
    ]
    FOOD_RELATION_CHOICES = [
        ('before_meal', _('Ovqatdan oldin')),
        ('with_meal', _('Ovqat paytida')),
        ('after_meal', _('Ovqatdan keyin')),
        ('none', _("Farqi yo'q")),
    ]
    STATUS_CHOICES = [
        ('active', _('Faol')),
        ('completed', _('Yakunlangan')),
        ('cancelled', _('Bekor qilingan')),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='medication_orders', verbose_name=_("Bemor kartasi")
    )
    prescribed_by = models.ForeignKey(
        'patients.Doctor', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='prescribed_medications',
        verbose_name=_("Tayinlagan shifokor")
    )

    medicine_name = models.CharField(max_length=255, verbose_name=_("Dori nomi"))
    medicine_type = models.CharField(
        max_length=15, choices=MEDICINE_TYPE_CHOICES, default='tablet',
        verbose_name=_("Dori turi")
    )

    duration_days = models.PositiveIntegerField(
        verbose_name=_("Davolash davomiyligi (kun)")
    )
    times_per_day = models.PositiveSmallIntegerField(
        verbose_name=_("Kuniga necha marta")
    )
    administration_times = models.JSONField(
        default=list, verbose_name=_("Qabul qilish vaqtlari"),
        help_text='["08:00", "14:00", "20:00"]'
    )
    food_relation = models.CharField(
        max_length=15, choices=FOOD_RELATION_CHOICES, default='none',
        verbose_name=_("Ovqat bilan bog'liqligi")
    )

    single_dose = models.CharField(
        max_length=100, blank=True, verbose_name=_("Bir martalik doza")
    )
    max_daily_dose = models.CharField(
        max_length=100, blank=True, verbose_name=_("Maksimal sutkalik doza")
    )
    special_instructions = models.TextField(
        blank=True, verbose_name=_("Maxsus ko'rsatmalar")
    )
    doctor_comment = models.TextField(blank=True, verbose_name=_("Shifokor izohi"))

    start_date = models.DateField(
        default=timezone.localdate, verbose_name=_("Boshlanish sanasi")
    )
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='active', verbose_name=_("Holati")
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_medication_orders',
        verbose_name=_("Yaratgan foydalanuvchi")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name=_("Dori/muolaja tayinlash")
        verbose_name_plural=_("Dori/muolaja tayinlashlar")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.medicine_name} — {self.patient_card}"


# ==================== HAMSHIRA VAZIFALARI ====================

class NurseTask(models.Model):
    TASK_TYPE_CHOICES = [
        ('medication', _('Dori berish')),
        ('injection', _('Ukol qilish')),
        ('consultation', _('Konsultatsiya')),
        ('diagnostic', _('Diagnostik tekshiruv')),
        ('lab', _('Laboratoriya tekshiruvi')),
        ('procedure', _('Muolaja')),
        ('other', _('Boshqa')),
    ]
    STATUS_CHOICES = [
        ('pending', _('Kutilmoqda')),
        ('done', _('Bajarildi')),
        ('delayed', _('Kechiktirildi')),
        ('cancelled', _('Bekor qilindi')),
        ('missed', _("O'tkazib yuborildi")),
    ]
    DELAY_REASON_CHOICES = [
        ('patient_absent', _('Bemor yo\'q edi')),
        ('patient_refused', _('Bemor rad etdi')),
        ('condition_worsened', _('Bemorning ahvoli og\'irlashdi')),
        ('medicine_unavailable', _('Dori mavjud emas')),
        ('device_broken', _('Qurilma nosoz')),
        ('other', _('Boshqa sabab')),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='nurse_tasks', verbose_name=_("Bemor kartasi")
    )
    task_type = models.CharField(
        max_length=15, choices=TASK_TYPE_CHOICES, verbose_name=_("Vazifa turi")
    )
    title = models.CharField(max_length=255, verbose_name=_("Sarlavha"))
    scheduled_at = models.DateTimeField(verbose_name=_("Bajarish vaqti"))
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name=_("Holati")
    )

    # Manba (MedicationOrder / Referral / ConsultationRequest / ...)
    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    source = GenericForeignKey('content_type', 'object_id')

    notes = models.TextField(blank=True, verbose_name=_("Izoh"))

    delay_reason = models.CharField(
        max_length=25, choices=DELAY_REASON_CHOICES, blank=True,
        verbose_name=_("Kechikish sababi")
    )
    delayed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Kechikkan vaqt"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name=_("Hamshira vazifasi")
        verbose_name_plural=_("Hamshira vazifalari")
        ordering            = ['scheduled_at']

    def __str__(self):
        return f"{self.scheduled_at:%d.%m.%Y %H:%M} — {self.title} ({self.patient_card})"

    @property
    def is_overdue(self):
        return self.status == 'pending' and self.scheduled_at < timezone.now()


class TaskCompletionLog(models.Model):
    ACTION_CHOICES = [
        ('done', _('Bajarildi')),
        ('delayed', _('Kechiktirildi')),
        ('cancelled', _('Bekor qilindi')),
        ('missed', _("O'tkazib yuborildi")),
    ]

    task = models.ForeignKey(
        NurseTask, on_delete=models.CASCADE,
        related_name='completion_logs', verbose_name=_("Vazifa")
    )
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='task_completion_logs',
        verbose_name=_("Bajaruvchi")
    )
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Bajarilgan vaqt"))
    action = models.CharField(max_length=10, choices=ACTION_CHOICES, verbose_name=_("Amal"))
    comment = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))
    delay_reason = models.CharField(
        max_length=25, choices=NurseTask.DELAY_REASON_CHOICES, blank=True,
        verbose_name=_("Kechikish sababi")
    )

    class Meta:
        verbose_name=_("Vazifa bajarilish logi")
        verbose_name_plural=_("Vazifa bajarilish loglari")
        ordering            = ['-performed_at']

    def __str__(self):
        return f"{self.task} — {self.get_action_display()} ({self.performed_at:%d.%m.%Y %H:%M})"


# ==================== FAVQULODDA HOLAT ====================

class EmergencyEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('condition_worsened', _("Bemorning ahvoli yomonlashdi")),
        ('allergic_reaction', _('Allergik reaksiya')),
        ('bp_change', _('Qon bosimi keskin o\'zgardi')),
        ('fainting', _('Hushdan ketish')),
        ('respiratory_failure', _('Nafas yetishmovchiligi')),
        ('other', _('Boshqa')),
    ]
    STATUS_CHOICES = [
        ('open', _('Ochiq')),
        ('acknowledged', _('Qabul qilindi')),
        ('resolved', _('Hal qilindi')),
    ]

    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='emergency_events', verbose_name=_("Bemor kartasi")
    )
    department = models.ForeignKey(
        'patients.Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='emergency_events',
        verbose_name=_("Bo'lim")
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reported_emergencies',
        verbose_name=_("Xabar bergan hamshira")
    )

    event_type = models.CharField(
        max_length=25, choices=EVENT_TYPE_CHOICES, verbose_name=_("Holat turi")
    )
    description = models.TextField(blank=True, verbose_name=_("Tasvir"))
    status = models.CharField(
        max_length=15, choices=STATUS_CHOICES, default='open', verbose_name=_("Holati")
    )

    occurred_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yuz bergan vaqt"))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Hal qilingan vaqt"))

    notified_doctors = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True,
        related_name='emergency_notifications', verbose_name=_("Xabar berilgan shifokorlar")
    )
    notified_head = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='emergency_head_notifications',
        verbose_name=_("Xabar berilgan bo'lim mudiri")
    )

    class Meta:
        verbose_name=_("Favqulodda holat")
        verbose_name_plural=_("Favqulodda holatlar")
        ordering            = ['-occurred_at']

    def __str__(self):
        return f"{self.get_event_type_display()} — {self.patient_card} ({self.occurred_at:%d.%m.%Y %H:%M})"


# ==================== BILDIRISHNOMALAR ====================

class Notification(models.Model):
    TYPE_CHOICES = [
        ('referral', _("Yo'llanma")),
        ('medication', _('Dori-muolaja')),
        ('task_due', _('Vazifa vaqti yetdi')),
        ('task_delayed', _('Vazifa kechikdi')),
        ('task_missed', _("Vazifa o'tkazib yuborildi")),
        ('emergency', _('Favqulodda holat')),
        ('other', _('Boshqa')),
    ]
    PRIORITY_CHOICES = [
        ('normal', _('Oddiy')),
        ('urgent', _('Shoshilinch')),
    ]

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='care_notifications',
        verbose_name=_("Qabul qiluvchi")
    )
    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        null=True, blank=True, related_name='care_notifications',
        verbose_name=_("Bemor kartasi")
    )

    notification_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='other', verbose_name=_("Turi")
    )
    title = models.CharField(max_length=255, verbose_name=_("Sarlavha"))
    message = models.TextField(blank=True, verbose_name=_("Xabar"))
    priority = models.CharField(
        max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name=_("Ustuvorlik")
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    related_object = GenericForeignKey('content_type', 'object_id')

    is_read = models.BooleanField(default=False, verbose_name=_("O'qilgan"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name=_("Bildirishnoma")
        verbose_name_plural=_("Bildirishnomalar")
        ordering            = ['-created_at']

    def __str__(self):
        target = self.recipient or self.patient_card
        return f"{target}: {self.title}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=['is_read'])


# ==================== AUDIT LOG ====================

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('created', _('Yaratildi')),
        ('updated', _('Yangilandi')),
        ('status_changed', _("Holat o'zgardi")),
        ('resolved', _('Hal qilindi')),
        ('deleted', _("O'chirildi")),
    ]

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='care_audit_logs',
        verbose_name=_("Bajardi")
    )
    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='care_audit_logs',
        verbose_name=_("Bemor kartasi")
    )

    content_type = models.ForeignKey(
        ContentType, on_delete=models.SET_NULL, null=True, blank=True
    )
    object_id = models.PositiveIntegerField(null=True, blank=True)
    target = GenericForeignKey('content_type', 'object_id')

    action = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name=_("Amal"))
    field_name = models.CharField(max_length=100, blank=True, verbose_name=_("Maydon"))
    old_value = models.TextField(blank=True, verbose_name=_("Eski qiymat"))
    new_value = models.TextField(blank=True, verbose_name=_("Yangi qiymat"))
    description = models.CharField(max_length=500, blank=True, verbose_name=_("Tavsif"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Vaqt"))

    class Meta:
        verbose_name=_("Audit log")
        verbose_name_plural=_("Audit loglar")
        ordering            = ['-created_at']

    def __str__(self):
        return f"[{self.created_at:%d.%m.%Y %H:%M}] {self.actor} — {self.get_action_display()}"
