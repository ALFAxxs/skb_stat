# apps/patients/models.py

from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Davlat"
        verbose_name_plural = "Davlatlar"


class Region(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Viloyat"
        verbose_name_plural = "Viloyatlar"


class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Tuman"
        verbose_name_plural = "Tumanlar"


class City(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Shahar"
        verbose_name_plural = "Shaharlar"


class Village(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Qishloq"
        verbose_name_plural = "Qishloqlar"


class Organization(models.Model):
    # Korxona asosiy ma'lumotlari
    enterprise_code = models.CharField(
        max_length=20, blank=True, verbose_name="Korxona kodi"
    )
    enterprise_inn = models.CharField(
        max_length=20, blank=True, verbose_name="Korxona INN"
    )
    enterprise_name = models.CharField(
        max_length=500, verbose_name="Korxona nomi"
    )
    # Filial ma'lumotlari
    branch_code = models.CharField(
        max_length=20, blank=True, verbose_name="Filial kodi"
    )
    branch_name = models.CharField(
        max_length=500, blank=True, verbose_name="Filial nomi"
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        if self.branch_name:
            return f"{self.enterprise_name} — {self.branch_name}"
        return self.enterprise_name

    @property
    def display_name(self):
        parts = []
        if self.enterprise_code:
            parts.append(self.enterprise_code)
        if self.branch_code:
            parts.append(self.branch_code)
        name = self.enterprise_name
        if self.branch_name:
            name += f" — {self.branch_name}"
        return f"[{'/'.join(parts)}] {name}" if parts else name

    class Meta:
        verbose_name = "Muassasa"
        verbose_name_plural = "Muassasalar"
        ordering = ['enterprise_name', 'branch_name']


class Department(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Bo'lim"
        verbose_name_plural = "Bo'limlar"


class HospitalType(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Shifoxona turi"
        verbose_name_plural = "Shifoxona turlari"


class OperationType(models.Model):
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name

    class Meta:
        verbose_name = "Amaliyot turi"
        verbose_name_plural = "Amaliyot turlari"
        ordering = ['name']


class Doctor(models.Model):
    full_name = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True)
    is_head = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.full_name

    class Meta:
        verbose_name = "Shifokor"
        verbose_name_plural = "Shifokorlar"


class DischargeConclusion(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Chiqish xulosasi"
        verbose_name_plural = "Chiqish xulosalari"


# ==================== ASOSIY MODEL ====================

class PatientCard(models.Model):

    # --- Bemor statusi ---
    STATUS_CHOICES = [
        ('registered', 'Registratsiya qilingan'),
        ('admitted', 'Yotqizilgan'),
        ('completed', 'Yakunlangan'),
    ]
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='registered',
        verbose_name="Bemor statusi"
    )

    # Kim registratsiya qilgani
    registered_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registered_patients',
        verbose_name="Registratsiya qilgan"
    )

    # --- 1. Tibbiy bayonnoma ---
    medical_record_number = models.CharField(max_length=50, unique=True)

    # --- 2. Bemor ma'lumotlari ---
    full_name = models.CharField(max_length=255)

    GENDER_CHOICES = [('M', 'Erkak'), ('F', 'Ayol')]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    birth_date = models.DateField()

    # --- Rezidentlik ---
    RESIDENT_CHOICES = [
        ('resident', 'Rezident'),
        ('non_resident', 'Norezident'),
    ]
    resident_status = models.CharField(
        max_length=15,
        choices=RESIDENT_CHOICES,
        default='resident'
    )

    # --- Bemor kategoriyasi ---
    PATIENT_CATEGORY_CHOICES = [
        ('railway', "Temir yo'lchi"),
        ('paid', 'Pullik'),
        ('non_resident', 'Norezident'),
    ]
    # resident_status endi patient_category dan aniqlanadi
    @property
    def is_non_resident(self):
        return self.patient_category == 'non_resident'

    @property
    def resident_status_display(self):
        return 'Norezident' if self.patient_category == 'non_resident' else 'Rezident'
    patient_category = models.CharField(
        max_length=15,
        choices=PATIENT_CATEGORY_CHOICES,
        default='railway',
        verbose_name="Bemor kategoriyasi"
    )

    # --- Kontakt ---
    phone = models.CharField(max_length=20, blank=True, verbose_name="Telefon raqami")
    JSHSHIR = models.CharField(max_length=14, blank=True, verbose_name="JSHSHIR")

    # --- Manzil ---
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    street_address = models.CharField(max_length=255, blank=True)

    # --- Ijtimoiy holat ---
    SOCIAL_STATUS_CHOICES = [
        ('employed', 'Ishlaydi'),
        ('unemployed', 'Vaqtincha ishsiz'),
        ('pensioner', 'Pensioner'),
        ('student_higher', 'Student'),
        ('student_school', "O'quvchi"),
        ('dependent', "Ota-ona qaramog'ida"),
    ]
    social_status = models.CharField(max_length=20, choices=SOCIAL_STATUS_CHOICES, blank=True)
    workplace = models.CharField(max_length=255, blank=True, verbose_name="Ish joyi / O'quv joyi")
    parent_name = models.CharField(max_length=255, blank=True, verbose_name="Ota-ona / Vasiy ismi")
    parent_jshshir = models.CharField(max_length=14, blank=True, verbose_name="Ota-ona JSHSHIR")
    parent_workplace_org = models.ForeignKey(
        'Organization', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children_patients', verbose_name="Ota-ona ish joyi"
    )
    workplace_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='employees',
        verbose_name="Ish joyi (ro'yxatdan)"
    )
    position = models.CharField(max_length=255, blank=True, verbose_name="Lavozimi")

    # --- Passport ---
    passport_serial = models.CharField(max_length=20, blank=True)

    # --- Kim olib kelgan ---
    REFERRAL_TYPE_CHOICES = [
        ('self', "O'zi kelgan"),
        ('ambulance', 'Tez tibbiy yordam'),
        ('referral', "Yo'llanma orqali"),
        ('liniya', "Liniya"),
    ]
    referral_type = models.CharField(max_length=20, choices=REFERRAL_TYPE_CHOICES, blank=True)
    referral_organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
    )

    # --- Tashxislar ---
    referring_diagnosis = models.TextField(blank=True)
    admission_diagnosis = models.TextField(blank=True)

    # --- Necha soat keyin ---
    HOURS_AFTER_ILLNESS_CHOICES = [
        ('under_6', 'Dastlabki 6 soat ichida'),
        ('7_to_24', '7-24 soat ichida'),
        ('over_24', '24 soatdan keyin'),
    ]
    hours_after_illness = models.CharField(
        max_length=10, choices=HOURS_AFTER_ILLNESS_CHOICES, blank=True
    )

    # --- Qo'shimcha ---
    is_emergency = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    is_pensioner = models.BooleanField(default=False, verbose_name="Pensioner")
    # is_pensioner endi social_status='pensioner' dan avtomatik aniqlanadi
    # BooleanField qoldirildi (eski ma'lumotlar uchun)

    # --- Shifoxona turi ---
    hospital_type = models.ForeignKey(
        HospitalType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Shifoxona turi"
    )

    # --- Statsionar/Ambulator ---
    IS_AMBULATORY_CHOICES = [
        ('inpatient', 'Statsionar (yotqizilgan)'),
        ('ambulatory', 'Ambulator (kunlik)'),
    ]
    visit_type = models.CharField(
        max_length=15,
        choices=IS_AMBULATORY_CHOICES,
        default='inpatient',
        blank=True,
        verbose_name="Tashrif turi"
    )

    # --- Yotqizilgan ---
    admission_date = models.DateTimeField()
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True,
        related_name='admissions'
    )

    # --- Qayta yotqizilish ---
    ADMISSION_COUNT_CHOICES = [
        ('first', 'Birinchi marta'),
        ('repeated', 'Qayta'),
    ]
    admission_count = models.CharField(
        max_length=10, choices=ADMISSION_COUNT_CHOICES, blank=True
    )

    # --- Necha kun ---
    days_in_hospital = models.PositiveIntegerField(default=0)

    # --- Chiqish ---
    OUTCOME_CHOICES = [
        ('discharged', 'Chiqarildi'),
        ('deceased', 'Vafot etdi'),
        ('transferred', "Boshqa shifoxonaga o'tkazildi"),
    ]
    outcome = models.CharField(max_length=15, choices=OUTCOME_CHOICES, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_conclusion = models.ForeignKey(
        DischargeConclusion, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Chiqish xulosasi"
    )

    # --- Yakuniy tashxis ---
    clinical_main_diagnosis = models.CharField(max_length=20, blank=True)
    clinical_main_diagnosis_text = models.TextField(blank=True)
    clinical_comorbidities = models.TextField(blank=True)

    pathological_main_diagnosis = models.CharField(max_length=20, blank=True)
    pathological_main_diagnosis_text = models.TextField(blank=True)
    pathological_comorbidities = models.TextField(blank=True)

    # --- Tekshiruvlar ---
    aids_test_date = models.DateField(null=True, blank=True)
    aids_test_result = models.CharField(max_length=50, blank=True)
    wp_test_date = models.DateField(null=True, blank=True)
    wp_test_result = models.CharField(max_length=50, blank=True)

    # --- Urush qatnashchisi ---
    is_war_veteran = models.BooleanField(default=False)

    # --- Shifokorlar ---
    attending_doctor = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attending_cards'
    )
    department_head = models.ForeignKey(
        Doctor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='head_cards'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # is_pensioner social_status dan avtomatik
        if self.social_status == 'pensioner':
            self.is_pensioner = True
        # Chiqish xulosasi qo'yilsa → completed
        if self.discharge_conclusion_id and self.status != 'completed':
            self.status = 'completed'
        # Shifokor qo'yilsa → admitted
        elif self.attending_doctor_id and self.status == 'registered':
            self.status = 'admitted'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.medical_record_number} - {self.full_name}"

    class Meta:
        verbose_name = "Bemor kartasi"
        verbose_name_plural = "Bemor kartalari"
        ordering = ['-admission_date']


# --- O'lim sabablari ---
class DeathCause(models.Model):
    patient_card = models.OneToOneField(
        PatientCard, on_delete=models.CASCADE, related_name='death_cause'
    )
    immediate_cause = models.TextField(blank=True)
    underlying_cause = models.TextField(blank=True)
    main_disease_code = models.CharField(max_length=20, blank=True)
    other_significant_conditions = models.TextField(blank=True)

    class Meta:
        verbose_name = "O'lim sababi"
        verbose_name_plural = "O'lim sabablari"


# --- Jarrohlik amaliyotlari ---
class SurgicalOperation(models.Model):
    patient_card = models.ForeignKey(
        PatientCard, on_delete=models.CASCADE, related_name='operations'
    )
    operation_date = models.DateField(null=True, blank=True)
    operation_type = models.ForeignKey(
        OperationType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Amaliyot turi"
    )
    operation_name = models.CharField(max_length=255, blank=True)
    ANESTHESIA_CHOICES = [
        ('yes', 'Narkoz bilan'),
        ('no', 'Narkozsiz'),
        ('local', 'Mahalliy narkoz'),
    ]
    anesthesia = models.CharField(max_length=10, choices=ANESTHESIA_CHOICES, blank=True)
    complication = models.TextField(blank=True)

    def __str__(self):
        name = self.operation_type or self.operation_name
        return f"{name} ({self.operation_date})"

    class Meta:
        verbose_name = "Jarrohlik amaliyoti"
        verbose_name_plural = "Jarrohlik amaliyotlari"


# --- MKB-10 ---
class ICD10Code(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title_uz = models.CharField(max_length=500)
    title_ru = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=5, blank=True)

    class Meta:
        ordering = ['code']
        verbose_name = "MKB-10 kodi"
        verbose_name_plural = "MKB-10 kodlari"

    def __str__(self):
        return f"{self.code} — {self.title_uz}"

class DepartmentTransfer(models.Model):
    """Bemor bo'limlar orasidagi ko'chirish tarixi"""
    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name="Bemor kartasi"
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transfers_from',
        verbose_name="Qayerdan"
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_to',
        verbose_name="Qayerga"
    )
    transferred_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ko'chirish sanasi"
    )
    transferred_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name="Kim ko'chirgan"
    )
    reason = models.TextField(blank=True, verbose_name="Sabab")

    class Meta:
        verbose_name = "Bo'lim ko'chirish"
        verbose_name_plural = "Bo'lim ko'chirishlar"
        ordering = ['-transferred_at']

    def __str__(self):
        return f"{self.patient_card} → {self.to_department}"
