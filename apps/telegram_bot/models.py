from django.db import models
from django.conf import settings
from django.utils import timezone
import secrets


class TelegramUser(models.Model):
    """Telegram orqali ro'yxatdan o'tgan foydalanuvchi"""
    LANG_CHOICES = [('uz', 'O\'zbek'), ('ru', 'Русский'), ('en', 'English')]

    telegram_id   = models.BigIntegerField(unique=True, verbose_name="Telegram ID")
    username      = models.CharField(max_length=64, blank=True, verbose_name="Username")
    first_name    = models.CharField(max_length=64, blank=True, verbose_name="Ismi")
    last_name     = models.CharField(max_length=64, blank=True, verbose_name="Familiyasi")
    phone         = models.CharField(max_length=20, blank=True, verbose_name="Telefon")
    language_code = models.CharField(
        max_length=5, choices=LANG_CHOICES,
        default='uz', verbose_name="Til"
    )
    is_verified   = models.BooleanField(default=False, verbose_name="Tasdiqlangan")
    is_blocked    = models.BooleanField(default=False, verbose_name="Bloklangan")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="Ro'yxatdan o'tgan")
    last_seen     = models.DateTimeField(auto_now=True, verbose_name="Oxirgi faollik")

    class Meta:
        verbose_name        = "Telegram foydalanuvchi"
        verbose_name_plural = "Telegram foydalanuvchilar"
        ordering            = ['-last_seen']

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip() or f"ID:{self.telegram_id}"
        return f"{name} (@{self.username})" if self.username else name

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or str(self.telegram_id)


class PatientTelegramBinding(models.Model):
    """Telegram foydalanuvchi ↔ Bemor kartasi bog'lanishi"""
    STATUS_CHOICES = [
        ('verified', 'Tasdiqlangan'),
        ('blocked',  'Bloklangan'),
    ]

    telegram_user = models.OneToOneField(
        TelegramUser, on_delete=models.CASCADE,
        related_name='patient_binding',
        verbose_name="Telegram foydalanuvchi"
    )
    patient_card = models.ForeignKey(
        'patients.PatientCard', on_delete=models.CASCADE,
        related_name='telegram_bindings',
        verbose_name="Bemor kartasi"
    )
    status      = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default='verified', verbose_name="Holat"
    )
    bound_phone = models.CharField(max_length=20, verbose_name="Tasdiqlangan raqam")
    bound_at    = models.DateTimeField(auto_now_add=True, verbose_name="Bog'langan vaqt")

    class Meta:
        verbose_name        = "Bemor-Telegram bog'lanishi"
        verbose_name_plural = "Bemor-Telegram bog'lanishlari"

    def __str__(self):
        return f"{self.telegram_user} → {self.patient_card.full_name}"


class ResultNotification(models.Model):
    """Laboratoriya natijasi bildirishnomasi"""
    STATUS_CHOICES = [
        ('pending', 'Yuborilmagan'),
        ('sent',    'Yuborildi'),
        ('seen',    'Ko\'rildi'),
        ('failed',  'Xato'),
    ]

    telegram_user = models.ForeignKey(
        TelegramUser, on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Foydalanuvchi"
    )
    lab_result = models.ForeignKey(
        'laboratory.LabResult', on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name="Lab natijasi"
    )
    status      = models.CharField(
        max_length=10, choices=STATUS_CHOICES,
        default='pending', verbose_name="Holat"
    )
    message_id  = models.BigIntegerField(
        null=True, blank=True,
        verbose_name="Telegram xabar ID"
    )
    sent_at     = models.DateTimeField(null=True, blank=True, verbose_name="Yuborilgan vaqt")
    seen_at     = models.DateTimeField(null=True, blank=True, verbose_name="Ko'rilgan vaqt")
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name="Urinishlar soni")
    error_msg   = models.TextField(blank=True, verbose_name="Xato matni")
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Bildirishnoma"
        verbose_name_plural = "Bildirishnomalar"
        ordering            = ['-created_at']
        unique_together     = ('telegram_user', 'lab_result')

    def __str__(self):
        return f"{self.telegram_user} | {self.lab_result} | {self.get_status_display()}"

    def mark_sent(self, message_id: int):
        self.status     = 'sent'
        self.message_id = message_id
        self.sent_at    = timezone.now()
        self.save(update_fields=['status', 'message_id', 'sent_at'])

    def mark_seen(self):
        if self.status != 'seen':
            self.status  = 'seen'
            self.seen_at = timezone.now()
            self.save(update_fields=['status', 'seen_at'])

    def mark_failed(self, error: str):
        self.status     = 'failed'
        self.retry_count += 1
        self.error_msg  = error[:500]
        self.save(update_fields=['status', 'retry_count', 'error_msg'])


class ResultFile(models.Model):
    """PDF natija fayli"""
    lab_result    = models.OneToOneField(
        'laboratory.LabResult', on_delete=models.CASCADE,
        related_name='pdf_file',
        verbose_name="Lab natijasi"
    )
    file_path     = models.CharField(max_length=500, blank=True, verbose_name="Fayl yo'li")
    telegram_file_id = models.CharField(
        max_length=200, blank=True,
        verbose_name="Telegram file_id (cache)"
    )
    secure_token  = models.CharField(
        max_length=64, unique=True,
        default=secrets.token_urlsafe,
        verbose_name="Xavfsiz token"
    )
    expires_at    = models.DateTimeField(verbose_name="Muddati")
    download_count = models.PositiveIntegerField(default=0, verbose_name="Yuklab olishlar")
    generated_at  = models.DateTimeField(auto_now_add=True, verbose_name="Yaratilgan vaqt")

    class Meta:
        verbose_name        = "Natija PDF fayli"
        verbose_name_plural = "Natija PDF fayllari"

    def __str__(self):
        return f"PDF #{self.lab_result_id} ({self.download_count} marta yuklangan)"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def increment_download(self):
        self.download_count += 1
        self.save(update_fields=['download_count'])


class AuditLog(models.Model):
    """Barcha bot amallarining audit logi"""
    ACTION_CHOICES = [
        ('start',        '/start'),
        ('auth',         'Autentifikatsiya'),
        ('auth_fail',    'Autentifikatsiya xatosi'),
        ('view_results', 'Natijalar ko\'rish'),
        ('view_result',  'Natija ko\'rish'),
        ('download_pdf', 'PDF yuklab olish'),
        ('menu',         'Menyu'),
        ('price_view',   'Narxlar ko\'rish'),
        ('blocked',      'Bloklandi'),
        ('error',        'Xato'),
    ]

    telegram_user = models.ForeignKey(
        TelegramUser, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='audit_logs',
        verbose_name="Foydalanuvchi"
    )
    telegram_id   = models.BigIntegerField(verbose_name="Telegram ID")
    action        = models.CharField(max_length=20, choices=ACTION_CHOICES, verbose_name="Amal")
    detail        = models.JSONField(default=dict, blank=True, verbose_name="Tafsilot")
    created_at    = models.DateTimeField(auto_now_add=True, verbose_name="Vaqt")

    class Meta:
        verbose_name        = "Audit log"
        verbose_name_plural = "Audit loglar"
        ordering            = ['-created_at']

    def __str__(self):
        return f"[{self.created_at:%d.%m.%Y %H:%M}] {self.telegram_id} → {self.get_action_display()}"

    @classmethod
    def write(cls, telegram_id: int, action: str, detail: dict = None, tg_user=None):
        cls.objects.create(
            telegram_id=telegram_id,
            telegram_user=tg_user,
            action=action,
            detail=detail or {},
        )


class BotConfig(models.Model):
    """Bot sozlamalari — faqat bitta yozuv (singleton)"""
    # Xush kelibsiz matni
    welcome_uz = models.TextField(default='👋 Xush kelibsiz!', verbose_name="Xush kelibsiz (UZ)")
    welcome_ru = models.TextField(default='👋 Добро пожаловать!', verbose_name="Xush kelibsiz (RU)")
    welcome_en = models.TextField(default='👋 Welcome!', verbose_name="Xush kelibsiz (EN)")

    # Klinika haqida
    about_uz = models.TextField(blank=True, verbose_name="Klinika haqida (UZ)")
    about_ru = models.TextField(blank=True, verbose_name="Klinika haqida (RU)")

    # Kontaktlar
    contacts = models.JSONField(
        default=dict, blank=True,
        verbose_name="Kontaktlar",
        help_text='{"phone": "+998...", "email": "...", "maps": "..."}'
    )

    # Ish vaqti
    working_hours = models.JSONField(
        default=dict, blank=True,
        verbose_name="Ish vaqti",
        help_text='{"mon-fri": "08:00-18:00", "sat": "08:00-14:00"}'
    )

    is_maintenance  = models.BooleanField(default=False, verbose_name="Texnik ishlar rejimi")
    maintenance_msg = models.TextField(blank=True, verbose_name="Texnik ishlar xabari")
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Bot sozlamalari"
        verbose_name_plural = "Bot sozlamalari"

    def __str__(self):
        return "Bot sozlamalari"

    def save(self, *args, **kwargs):
        self.pk = 1  # Singleton
        super().save(*args, **kwargs)

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def get_welcome(self, lang='uz'):
        return getattr(self, f'welcome_{lang}', self.welcome_uz)

    def get_about(self, lang='uz'):
        return getattr(self, f'about_{lang}', self.about_uz)
