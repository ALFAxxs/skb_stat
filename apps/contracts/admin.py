# apps/contracts/admin.py

from django.contrib import admin
from apps.contracts.models import Contract


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display  = ['contract_number', 'patient_card', 'contract_type', 'status', 'contract_date']
    list_filter   = ['contract_type', 'status', 'contract_date']
    search_fields = ['contract_number', 'patient_card__full_name']
    readonly_fields = ['verify_token', 'created_at', 'updated_at']