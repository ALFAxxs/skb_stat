# apps/queue_app/admin.py

from django.contrib import admin
from apps.queue_app.models import QueueTicket, QueueSettings


@admin.register(QueueTicket)
class QueueTicketAdmin(admin.ModelAdmin):
    list_display  = ['ticket_number', 'patient_card', 'status', 'room', 'created_at']
    list_filter   = ['status', 'room', 'created_at']
    search_fields = ['patient_card__full_name', 'ticket_number']
    list_editable = ['status']
    ordering      = ['-created_at']
    readonly_fields = ['created_at', 'called_at', 'served_at', 'done_at']


@admin.register(QueueSettings)
class QueueSettingsAdmin(admin.ModelAdmin):
    list_display = ['audio_mode', 'updated_at']