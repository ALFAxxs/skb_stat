# apps/care/admin.py

from django.contrib import admin

from .models import (
    AuditLog, EmergencyEvent, MedicationOrder, NurseTask, Notification, Referral,
    TaskCompletionLog,
)


@admin.register(Referral)
class ReferralAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient_card', 'referring_doctor', 'target_doctor',
        'service_type', 'priority', 'status', 'scheduled_at', 'created_at',
    ]
    list_filter = ['service_type', 'priority', 'status']
    search_fields = ['patient_card__full_name', 'service_detail', 'comment']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at']


@admin.register(MedicationOrder)
class MedicationOrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient_card', 'medicine_name', 'medicine_type',
        'duration_days', 'times_per_day', 'status', 'start_date',
    ]
    list_filter = ['medicine_type', 'food_relation', 'status']
    search_fields = ['patient_card__full_name', 'medicine_name']
    date_hierarchy = 'start_date'
    readonly_fields = ['created_at', 'updated_at']


class TaskCompletionLogInline(admin.TabularInline):
    model = TaskCompletionLog
    extra = 0
    readonly_fields = ['performed_by', 'performed_at', 'action', 'comment', 'delay_reason']
    can_delete = False


@admin.register(NurseTask)
class NurseTaskAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient_card', 'task_type', 'title',
        'scheduled_at', 'status', 'delay_reason', 'is_overdue',
    ]
    list_filter = ['task_type', 'status', 'delay_reason']
    search_fields = ['patient_card__full_name', 'title']
    date_hierarchy = 'scheduled_at'
    readonly_fields = ['created_at', 'updated_at']
    inlines = [TaskCompletionLogInline]


@admin.register(TaskCompletionLog)
class TaskCompletionLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'task', 'performed_by', 'action', 'performed_at']
    list_filter = ['action']
    search_fields = ['task__title', 'task__patient_card__full_name']


@admin.register(EmergencyEvent)
class EmergencyEventAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'patient_card', 'department', 'event_type',
        'status', 'reported_by', 'occurred_at', 'resolved_at',
    ]
    list_filter = ['event_type', 'status', 'department']
    search_fields = ['patient_card__full_name', 'description']
    date_hierarchy = 'occurred_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'recipient', 'patient_card', 'notification_type',
        'title', 'priority', 'is_read', 'created_at',
    ]
    list_filter = ['notification_type', 'priority', 'is_read']
    search_fields = ['title', 'message', 'recipient__username', 'patient_card__full_name']
    date_hierarchy = 'created_at'


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'actor', 'patient_card', 'action', 'field_name',
        'content_type', 'object_id', 'created_at',
    ]
    list_filter = ['action', 'content_type']
    search_fields = ['patient_card__full_name', 'description', 'field_name']
    date_hierarchy = 'created_at'
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
