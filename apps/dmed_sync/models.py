"""
DMED Sync Queue — har bir o'zgargan entity uchun sinxronizatsiya yozuvi.
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class DMEDSyncRecord(models.Model):

    ENTITY_PATIENT    = 'patient'
    ENTITY_VISIT      = 'visit'
    ENTITY_SERVICE    = 'patient_service'
    ENTITY_LAB        = 'lab_result'
    ENTITY_DIAGNOSTIC = 'diagnostic'
    ENTITY_CONSULT    = 'consultation'

    ENTITY_CHOICES = [
        (ENTITY_PATIENT,    'Bemor kartasi'),
        (ENTITY_VISIT,      'Qabul (statsionar/ambulator)'),
        (ENTITY_SERVICE,    'Bemor xizmati'),
        (ENTITY_LAB,        'Tahlil natijasi'),
        (ENTITY_DIAGNOSTIC, 'Diagnostika natijasi'),
        (ENTITY_CONSULT,    'Konsultatsiya'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_RUNNING = 'running'
    STATUS_DONE    = 'done'
    STATUS_FAILED  = 'failed'
    STATUS_SKIP    = 'skipped'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Kutilmoqda'),
        (STATUS_RUNNING, 'Jarayonda'),
        (STATUS_DONE,    'Bajarildi'),
        (STATUS_FAILED,  'Xato'),
        (STATUS_SKIP,    'O\'tkazildi'),
    ]

    entity_type = models.CharField(max_length=30, choices=ENTITY_CHOICES, verbose_name='Entity turi')
    entity_id   = models.PositiveIntegerField(verbose_name='Entity ID')
    entity_repr = models.CharField(max_length=255, blank=True, verbose_name='Tavsif')

    status      = models.CharField(max_length=10, choices=STATUS_CHOICES,
                                   default=STATUS_PENDING, db_index=True)
    dmed_id     = models.CharField(max_length=100, blank=True,
                                   verbose_name='DMED ID (muvaffaqiyatli bo\'lsa)')
    error       = models.TextField(blank=True, verbose_name='Xato matni')
    attempts    = models.PositiveSmallIntegerField(default=0)

    enqueued_at      = models.DateTimeField(auto_now_add=True)
    last_attempt_at  = models.DateTimeField(null=True, blank=True)
    synced_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'DMED Sync yozuvi'
        verbose_name_plural = 'DMED Sync yozuvlari'
        ordering            = ['-enqueued_at']
        indexes = [
            models.Index(fields=['status', 'enqueued_at']),
            models.Index(fields=['entity_type', 'entity_id']),
        ]

    def __str__(self):
        return f"{self.get_entity_type_display()} #{self.entity_id} — {self.get_status_display()}"

    def mark_running(self):
        self.status = self.STATUS_RUNNING
        self.attempts += 1
        self.last_attempt_at = timezone.now()
        self.save(update_fields=['status', 'attempts', 'last_attempt_at'])

    def mark_done(self, dmed_id=''):
        self.status   = self.STATUS_DONE
        self.dmed_id  = dmed_id
        self.error    = ''
        self.synced_at = timezone.now()
        self.save(update_fields=['status', 'dmed_id', 'error', 'synced_at'])

    def mark_failed(self, error: str):
        self.status = self.STATUS_FAILED
        self.error  = error[:2000]
        self.save(update_fields=['status', 'error'])

    @classmethod
    def enqueue(cls, entity_type: str, entity_id: int, entity_repr: str = '') -> 'DMEDSyncRecord':
        """Mavjud bo'lsa qayta pending ga tushiradi, yo'qsa yangi yaratadi."""
        obj, created = cls.objects.update_or_create(
            entity_type=entity_type,
            entity_id=entity_id,
            defaults={
                'status':      cls.STATUS_PENDING,
                'entity_repr': entity_repr,
                'error':       '',
            }
        )
        return obj


class DMEDSession(models.Model):
    """
    Playwright storage_state saqlash.
    Bitta yozuv bo'ladi (pk=1), `dmed_login` buyrug'i yangilab turadi.
    """
    storage_state_json = models.TextField(
        blank=True,
        verbose_name='Storage state (cookies + localStorage)'
    )
    logged_in_at  = models.DateTimeField(null=True, blank=True)
    logged_in_by  = models.CharField(max_length=100, blank=True, verbose_name='Kim login qildi')
    is_valid      = models.BooleanField(default=False)
    last_used_at  = models.DateTimeField(null=True, blank=True)
    last_error    = models.TextField(blank=True)

    class Meta:
        verbose_name = 'DMED Session'

    def __str__(self):
        state = "Faol" if self.is_valid else "Nofaol"
        since = self.logged_in_at.strftime('%d.%m.%Y %H:%M') if self.logged_in_at else "—"
        return f"DMED Session — {state} ({since})"

    @classmethod
    def get_latest(cls):
        return cls.objects.order_by('-logged_in_at').first()

    @classmethod
    def save_state(cls, storage_state: dict, logged_in_by: str = ''):
        from django.utils import timezone
        obj, _ = cls.objects.update_or_create(
            pk=1,
            defaults={
                'storage_state_json': __import__('json').dumps(storage_state),
                'logged_in_at':       timezone.now(),
                'logged_in_by':       logged_in_by,
                'is_valid':           True,
                'last_error':         '',
            }
        )
        return obj
