# apps/billing/admin.py

from django.contrib import admin
from .models import Invoice, Payment, Discount, Refund, Consumable, PatientConsumable, BillingAuditLog


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient_card', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'patient_card__full_name')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'cashier', 'created_at')
    list_filter = ('method',)
    search_fields = ('invoice__invoice_number',)


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'reason', 'created_by', 'created_at')
    search_fields = ('invoice__invoice_number',)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'reason', 'created_by', 'created_at')
    search_fields = ('invoice__invoice_number',)


@admin.register(Consumable)
class ConsumableAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'price', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)


@admin.register(PatientConsumable)
class PatientConsumableAdmin(admin.ModelAdmin):
    list_display = ('patient_card', 'consumable', 'quantity', 'price', 'ordered_at')
    search_fields = ('patient_card__full_name', 'consumable__name')


@admin.register(BillingAuditLog)
class BillingAuditLogAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'action', 'actor', 'created_at')
    list_filter = ('action',)
    search_fields = ('invoice__invoice_number',)
