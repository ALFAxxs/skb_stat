# apps/laboratory/admin.py

from django.contrib import admin

from .models import (
    LabParameter,
    LabParameterGroup,
    LabResult,
    LabResultValue,
    LabTemplate,
)


class LabParameterGroupInline(admin.TabularInline):
    model = LabParameterGroup
    extra = 1
    fields = ('name', 'sort_order')


class LabParameterInline(admin.TabularInline):
    model = LabParameter
    extra = 1
    fields = (
        'name', 'name_ru', 'unit', 'param_type', 'group',
        'normal_min', 'normal_max',
        'normal_min_m', 'normal_max_m',
        'normal_min_f', 'normal_max_f',
        'sort_order',
    )


@admin.register(LabTemplate)
class LabTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'parameter_count')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    inlines = [LabParameterGroupInline, LabParameterInline]

    def parameter_count(self, obj):
        return obj.parameters.count()
    parameter_count.short_description = 'Parametrlar soni'


@admin.register(LabParameterGroup)
class LabParameterGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'template', 'sort_order')
    list_filter = ('template',)
    search_fields = ('name',)


@admin.register(LabParameter)
class LabParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_ru', 'template', 'group', 'unit', 'param_type', 'sort_order')
    list_filter = ('template', 'param_type')
    search_fields = ('name', 'name_ru')
    fieldsets = (
        ('Asosiy', {
            'fields': ('template', 'group', 'name', 'name_ru', 'unit', 'param_type', 'sort_order')
        }),
        ("Umumiy me'yor", {
            'fields': ('normal_min', 'normal_max')
        }),
        ('Kritik chegaralar', {
            'fields': ('critical_min', 'critical_max'),
            'classes': ('collapse',),
        }),
        ("Erkaklar me'yori", {
            'fields': ('normal_min_m', 'normal_max_m'),
            'classes': ('collapse',),
        }),
        ("Ayollar me'yori", {
            'fields': ('normal_min_f', 'normal_max_f'),
            'classes': ('collapse',),
        }),
        ('Tanlov variantlari', {
            'fields': ('select_options',),
            'classes': ('collapse',),
        }),
    )


class LabResultValueInline(admin.TabularInline):
    model = LabResultValue
    extra = 0
    fields = ('parameter', 'value', 'value_status', 'comment')
    readonly_fields = ('parameter',)


@admin.register(LabResult)
class LabResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'patient_card', 'template', 'status', 'created_by', 'created_at')
    list_filter = ('status', 'template', 'created_at')
    search_fields = ('patient_card__full_name', 'patient_card__medical_record_number')
    readonly_fields = ('created_at', 'printed_at')
    inlines = [LabResultValueInline]
    date_hierarchy = 'created_at'


@admin.register(LabResultValue)
class LabResultValueAdmin(admin.ModelAdmin):
    list_display = ('result', 'parameter', 'value', 'value_status', 'comment')
    list_filter = ('value_status',)
    search_fields = ('result__patient_card__full_name', 'parameter__name', 'value')
