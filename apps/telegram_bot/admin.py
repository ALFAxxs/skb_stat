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


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not BotConfig.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
