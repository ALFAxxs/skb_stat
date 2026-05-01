# apps/services/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import ServiceCategory, Service, PatientService


class ServiceInline(admin.TabularInline):
    model = Service
    extra = 1
    fields = ['code', 'name', 'price_normal', 'price_railway', 'is_active', 'is_operation']


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    inlines = [ServiceInline]
    list_display = ['icon', 'name', 'code', 'category_type', 'is_active']
    list_filter = ['category_type', 'is_active']
    search_fields = ['name', 'code']
    list_editable = ['is_active']


def mark_as_operation(modeladmin, request, queryset):
    updated = queryset.update(is_operation=True)
    modeladmin.message_user(request, f"✅ {updated} ta xizmat operatsiya deb belgilandi.")
mark_as_operation.short_description = "✅ Operatsiya deb belgilash"

def unmark_as_operation(modeladmin, request, queryset):
    updated = queryset.update(is_operation=False)
    modeladmin.message_user(request, f"❌ {updated} ta xizmatdan operatsiya belgisi olib tashlandi.")
unmark_as_operation.short_description = "❌ Operatsiya belgisini olib tashlash"


class IsOperationFilter(admin.SimpleListFilter):
    title = "Operatsiyami?"
    parameter_name = "is_op"

    def lookups(self, request, model_admin):
        return [
            ('yes', '✅ Ha — operatsiya'),
            ('no',  '❌ Yo\'q — oddiy xizmat'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(is_operation=True)
        if self.value() == 'no':
            return queryset.filter(is_operation=False)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        'code', 'name', 'category',
        'price_normal', 'price_railway',
        'is_operation_badge', 'is_active',
    ]
    list_filter = [IsOperationFilter, 'category', 'department', 'is_active']
    search_fields = ['name', 'code']
    # is_operation ni to'g'ridan ro'yxatda o'zgartirib bo'ladi
    list_editable = ['is_active']
    actions = [mark_as_operation, unmark_as_operation]

    # Kategoriya bo'yicha guruhlash
    list_per_page = 50

    def is_operation_badge(self, obj):
        if obj.is_operation:
            return format_html(
                '<span style="background:#198754;color:#fff;padding:2px 10px;'
                'border-radius:12px;font-size:12px;font-weight:600;">🔪 Ha</span>'
            )
        return format_html(
            '<span style="background:#f8f9fa;color:#6c757d;padding:2px 10px;'
            'border-radius:12px;font-size:12px;border:1px solid #dee2e6;">—</span>'
        )
    is_operation_badge.short_description = "Operatsiya"
    is_operation_badge.admin_order_field = 'is_operation'

    # Har bir xizmatni ochmasdan inline o'zgartirish uchun
    def get_list_editable(self, request):
        return self.list_editable


@admin.register(PatientService)
class PatientServiceAdmin(admin.ModelAdmin):
    list_display = [
        'patient_card', 'service', 'quantity',
        'price', 'total_price_display',
        'status', 'is_paid', 'ordered_at'
    ]
    list_filter = ['status', 'is_paid', 'service__category', 'patient_category_at_order']
    search_fields = ['patient_card__full_name', 'patient_card__medical_record_number']
    readonly_fields = ['ordered_at', 'patient_category_at_order']

    def total_price_display(self, obj):
        return f"{obj.total_price:,.0f} so'm"
    total_price_display.short_description = "Jami narx"


from .models import Medicine, PatientMedicine

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'is_active']
    list_filter = ['unit', 'is_active']
    search_fields = ['name']

@admin.register(PatientMedicine)
class PatientMedicineAdmin(admin.ModelAdmin):
    list_display = ['patient_card', 'medicine', 'quantity', 'price', 'ordered_by', 'ordered_at']
    list_filter = ['medicine__unit']
    search_fields = ['medicine__name', 'patient_card__full_name']