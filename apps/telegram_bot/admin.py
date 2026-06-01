from django import forms
from django.contrib import admin
from .models import (
    TelegramUser, PatientTelegramBinding,
    ResultNotification, ResultFile,
    AuditLog, BotConfig,
)


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display  = ('telegram_id', 'full_name', 'username', 'phone',
                      'language_code', 'is_verified', 'is_blocked', 'last_seen')
    list_filter   = ('is_verified', 'is_blocked', 'language_code')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name', 'phone')
    readonly_fields = ('telegram_id', 'created_at', 'last_seen')
    actions       = ['block_users', 'unblock_users']

    @admin.action(description='Bloklash')
    def block_users(self, request, qs):
        qs.update(is_blocked=True)

    @admin.action(description='Blokdan chiqarish')
    def unblock_users(self, request, qs):
        qs.update(is_blocked=False)


@admin.register(PatientTelegramBinding)
class PatientTelegramBindingAdmin(admin.ModelAdmin):
    list_display  = ('telegram_user', 'patient_card', 'bound_phone', 'status', 'bound_at')
    list_filter   = ('status',)
    search_fields = ('telegram_user__telegram_id', 'patient_card__full_name', 'bound_phone')
    readonly_fields = ('bound_at',)


@admin.register(ResultNotification)
class ResultNotificationAdmin(admin.ModelAdmin):
    list_display  = ('telegram_user', 'lab_result', 'status', 'retry_count', 'sent_at', 'seen_at')
    list_filter   = ('status',)
    search_fields = ('telegram_user__telegram_id',)
    readonly_fields = ('created_at', 'sent_at', 'seen_at')


@admin.register(ResultFile)
class ResultFileAdmin(admin.ModelAdmin):
    list_display  = ('lab_result', 'download_count', 'is_expired', 'generated_at')
    readonly_fields = ('secure_token', 'generated_at', 'download_count')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'telegram_id', 'action', 'telegram_user')
    list_filter   = ('action',)
    search_fields = ('telegram_id',)
    readonly_fields = ('created_at', 'telegram_id', 'telegram_user', 'action', 'detail')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class BotConfigForm(forms.ModelForm):
    # Kontaktlar — oddiy maydonlar
    contact_phone   = forms.CharField(label="Telefon raqami", required=False,
                                      help_text="Masalan: +998 71 299-62-90")
    contact_phone2  = forms.CharField(label="Telefon raqami 2", required=False)
    contact_email   = forms.CharField(label="E-mail", required=False)
    contact_address = forms.CharField(label="Manzil", required=False,
                                      widget=forms.Textarea(attrs={'rows': 2}))
    contact_maps    = forms.CharField(label="Google Maps havolasi", required=False)

    # Ish vaqti — oddiy maydonlar
    hours_weekday   = forms.CharField(label="Dushanba–Juma", required=False,
                                      help_text="Masalan: 08:00 – 17:00")
    hours_saturday  = forms.CharField(label="Shanba", required=False,
                                      help_text="Masalan: 08:00 – 13:00, yoki 'Dam olish kuni'")
    hours_sunday    = forms.CharField(label="Yakshanba", required=False,
                                      help_text="Masalan: Dam olish kuni")

    class Meta:
        model  = BotConfig
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            c = self.instance.contacts or {}
            self.fields['contact_phone'].initial   = c.get('phone', '')
            self.fields['contact_phone2'].initial  = c.get('phone2', '')
            self.fields['contact_email'].initial   = c.get('email', '')
            self.fields['contact_address'].initial = c.get('address', '')
            self.fields['contact_maps'].initial    = c.get('maps', '')

            h = self.instance.working_hours or {}
            self.fields['hours_weekday'].initial  = h.get('mon_fri', '')
            self.fields['hours_saturday'].initial = h.get('sat', '')
            self.fields['hours_sunday'].initial   = h.get('sun', '')

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.contacts = {
            'phone':   self.cleaned_data.get('contact_phone', ''),
            'phone2':  self.cleaned_data.get('contact_phone2', ''),
            'email':   self.cleaned_data.get('contact_email', ''),
            'address': self.cleaned_data.get('contact_address', ''),
            'maps':    self.cleaned_data.get('contact_maps', ''),
        }
        instance.working_hours = {
            'mon_fri': self.cleaned_data.get('hours_weekday', ''),
            'sat':     self.cleaned_data.get('hours_saturday', ''),
            'sun':     self.cleaned_data.get('hours_sunday', ''),
        }
        if commit:
            instance.save()
        return instance


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    form = BotConfigForm
    fieldsets = (
        ("🏥 Klinika haqida", {
            'fields': ('about_uz', 'about_ru'),
        }),
        ("📞 Kontaktlar", {
            'fields': (
                'contact_phone', 'contact_phone2',
                'contact_email', 'contact_address', 'contact_maps',
            ),
        }),
        ("🕐 Ish vaqti", {
            'fields': ('hours_weekday', 'hours_saturday', 'hours_sunday'),
        }),
        ("👋 Xush kelibsiz matni", {
            'fields': ('welcome_uz', 'welcome_ru', 'welcome_en'),
            'classes': ('collapse',),
        }),
        ("⚙️ Texnik sozlamalar", {
            'fields': ('is_maintenance', 'maintenance_msg'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        return not BotConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        # Ro'yxat o'rniga to'g'ridan-to'g'ri tahrirlash sahifasiga o'tish
        obj, _ = BotConfig.objects.get_or_create(pk=1)
        from django.shortcuts import redirect
        return redirect(f'/admin/telegram_bot/botconfig/{obj.pk}/change/')
