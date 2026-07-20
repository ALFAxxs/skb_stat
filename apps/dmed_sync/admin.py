from django.contrib import admin
from .models import DMEDSyncRecord, DMEDSession


@admin.register(DMEDSyncRecord)
class DMEDSyncRecordAdmin(admin.ModelAdmin):
    list_display  = ['entity_type', 'entity_id', 'entity_repr', 'status',
                     'attempts', 'enqueued_at', 'synced_at']
    list_filter   = ['status', 'entity_type']
    search_fields = ['entity_repr', 'dmed_id', 'error']
    readonly_fields = ['enqueued_at', 'last_attempt_at', 'synced_at']
    actions = ['retry_selected']

    @admin.action(description='Tanlanganlarni qayta navbatga qo\'yish')
    def retry_selected(self, request, queryset):
        queryset.update(status=DMEDSyncRecord.STATUS_PENDING, attempts=0, error='')


@admin.register(DMEDSession)
class DMEDSessionAdmin(admin.ModelAdmin):
    list_display = ['pk', 'is_valid', 'logged_in_at']
    readonly_fields = ['logged_in_at']
