# apps/patients/admin.py

from django.contrib import admin
from .models import (
    PatientCard, DeathCause, SurgicalOperation,
    Organization, Department, Doctor, DischargeConclusion,
    Country, Region, District, City, Village,
    HospitalType, OperationType, ICD10Code,
    InitialExamination, EpisodeDiagnosis,
)

# ==================== INLINE ADMINLAR ====================

class SurgicalOperationInline(admin.TabularInline):
    model = SurgicalOperation
    extra = 1
    fields = ['operation_date', 'operation_type', 'anesthesia', 'complication']


class DeathCauseInline(admin.StackedInline):
    model = DeathCause
    extra = 0
    max_num = 1
    fields = [
        'immediate_cause', 'underlying_cause',
        'main_disease_code', 'other_significant_conditions'
    ]


# ==================== ASOSIY ADMIN ====================

@admin.register(PatientCard)
class PatientCardAdmin(admin.ModelAdmin):
    inlines = [SurgicalOperationInline, DeathCauseInline]
    list_display = [
        'medical_record_number', 'full_name', 'gender',
        'admission_date', 'department', 'status', 'outcome', 'attending_doctor'
    ]
    list_filter = [
        'gender', 'outcome', 'status', 'department',
        'social_status', 'is_emergency', 'is_paid',
        'admission_count', 'is_war_veteran', 'resident_status',
        'patient_category'
    ]
    search_fields = ['full_name', 'medical_record_number', 'case_sheet_number', 'passport_serial', 'JSHSHIR', 'phone']
    list_per_page = 50
    date_hierarchy = 'admission_date'
    ordering      = ['-admission_date']
    list_display_links = ['medical_record_number', 'full_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ("Bemor statusi", {
            'fields': ('status', 'registered_by')
        }),
        ("Bemor ma'lumotlari", {
            'fields': (
                'medical_record_number', 'full_name', 'gender',
                'birth_date', 'social_status', 'passport_serial',
                'JSHSHIR', 'phone', 'resident_status', 'patient_category',
                'workplace', 'position',
            )
        }),
        ("Yashash manzili", {
            'fields': (
                'country', 'region', 'district', 'city',
                'village', 'street_address',
            )
        }),
        ("Qabul ma'lumotlari", {
            'fields': (
                'referral_type', 'referral_organization',
                'referring_diagnosis', 'admission_diagnosis',
                'hours_after_illness', 'is_emergency', 'is_paid',
                'hospital_type', 'admission_date', 'department', 'admission_count'
            )
        }),
        ("Chiqish ma'lumotlari", {
            'fields': (
                'days_in_hospital', 'outcome',
                'discharge_conclusion', 'discharge_date',
            )
        }),
        ("Yakuniy tashxis", {
            'fields': (
                'clinical_main_diagnosis', 'clinical_main_diagnosis_text',
                'clinical_comorbidities',
                'pathological_main_diagnosis', 'pathological_main_diagnosis_text',
                'pathological_comorbidities',
            )
        }),
        ("Tekshiruvlar", {
            'fields': (
                'aids_test_date', 'aids_test_result',
                'wp_test_date', 'wp_test_result',
                'is_war_veteran'
            )
        }),
        ("Shifokorlar", {
            'fields': ('attending_doctor', 'department_head')
        }),
        ("Tizim", {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(HospitalType)
class HospitalTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']


@admin.register(OperationType)
class OperationTypeAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['code', 'name']


@admin.register(DischargeConclusion)
class DischargeConclusionAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    list_editable = ['is_active']
    search_fields = ['name']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = [
        'enterprise_name', 'branch_name',
        'enterprise_code', 'branch_code',
        'enterprise_inn', 'is_active'
    ]
    search_fields = [
        'enterprise_name', 'branch_name',
        'enterprise_code', 'branch_code', 'enterprise_inn'
    ]
    list_filter = ['is_active']
    list_editable = ['is_active']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active']
    search_fields = ['name']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'department', 'is_head', 'is_general_practitioner', 'is_active']
    list_filter = ['department', 'is_head', 'is_general_practitioner', 'is_active']
    search_fields = ['full_name']


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ['name', 'country']
    search_fields = ['name']
    list_filter = ['country']


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ['name', 'region']
    search_fields = ['name']
    list_filter = ['region']


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ['name', 'district']
    search_fields = ['name']
    list_filter = ['district']


@admin.register(ICD10Code)
class ICD10CodeAdmin(admin.ModelAdmin):
    list_display = ['code', 'title_uz', 'category']
    search_fields = ['code', 'title_uz']
    list_filter = ['category']


@admin.register(InitialExamination)
class InitialExaminationAdmin(admin.ModelAdmin):
    list_display  = ['patient_card', 'created_at', 'updated_at']
    search_fields = ['patient_card__full_name', 'patient_card__medical_record_number']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        (None, {'fields': ('patient_card',)}),
        ("Ko'rik ma'lumotlari", {'fields': (
            'complaints', 'anamnesis_morbi', 'anamnesis_vitae',
            'status_localis', 'epidemiological_anamnesis', 'status_praesens',
            'allergy_anamnesis', 'neurological_status', 'lab_investigations',
        )}),
        ("Tizim", {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',)}),
    )


@admin.register(EpisodeDiagnosis)
class EpisodeDiagnosisAdmin(admin.ModelAdmin):
    list_display  = ['patient_card', 'icd10_code', 'diagnosis_type', 'diagnosis_role', 'created_at']
    list_filter   = ['diagnosis_type', 'diagnosis_role']
    search_fields = ['patient_card__full_name', 'icd10_code__code', 'clinical_text']
    autocomplete_fields = ['icd10_code']