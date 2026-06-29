# apps/patients/models.py

from django.db import models
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Davlat")
        verbose_name_plural = _("Davlatlar")


class Region(models.Model):
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Viloyat")
        verbose_name_plural = _("Viloyatlar")


class District(models.Model):
    region = models.ForeignKey(Region, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Tuman")
        verbose_name_plural = _("Tumanlar")


class City(models.Model):
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Shahar")
        verbose_name_plural = _("Shaharlar")


class Village(models.Model):
    city = models.ForeignKey(City, on_delete=models.CASCADE, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Qishloq")
        verbose_name_plural = _("Qishloqlar")


class Organization(models.Model):
    # Korxona asosiy ma'lumotlari
    enterprise_code = models.CharField(
        max_length=20, blank=True, verbose_name=_("Korxona kodi")
    )
    enterprise_inn = models.CharField(
        max_length=20, blank=True, verbose_name=_("Korxona INN")
    )
    enterprise_name = models.CharField(
        max_length=500, verbose_name=_("Korxona nomi")
    )
    # Filial ma'lumotlari
    branch_code = models.CharField(
        max_length=20, blank=True, verbose_name=_("Filial kodi")
    )
    branch_name = models.CharField(
        max_length=500, blank=True, verbose_name=_("Filial nomi")
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
        verbose_name = _("Muassasa")
        verbose_name_plural = _("Muassasalar")
        ordering = ['enterprise_name', 'branch_name']


class Department(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Bo'lim")
        verbose_name_plural = _("Bo'limlar")


class HospitalType(models.Model):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Shifoxona turi")
        verbose_name_plural = _("Shifoxona turlari")


class OperationType(models.Model):
    code = models.CharField(max_length=20, blank=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} — {self.name}" if self.code else self.name

    class Meta:
        verbose_name = _("Amaliyot turi")
        verbose_name_plural = _("Amaliyot turlari")
        ordering = ['name']


class DischargeConclusion(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("Chiqish xulosasi")
        verbose_name_plural = _("Chiqish xulosalari")


# ==================== ASOSIY MODEL ====================

class PatientCard(models.Model):

    # --- Bemor statusi ---
    STATUS_CHOICES = [
        ('registered', _('Registratsiya qilingan')),
        ('admitted', _('Yotqizilgan')),
        ('completed', _('Yakunlangan')),
    ]
    status = models.CharField(
        max_length=15,
        choices=STATUS_CHOICES,
        default='registered',
        verbose_name=_("Bemor statusi")
    )

    # Kim registratsiya qilgani
    registered_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='registered_patients',
        verbose_name=_("Registratsiya qilgan")
    )

    # --- 1. Tibbiy bayonnoma ---
    medical_record_number = models.CharField(max_length=50, unique=True)
    case_sheet_number = models.CharField(
        max_length=50, blank=True,
        verbose_name=_("Kasallik varaqasi tartib raqami")
    )

    # --- 2. Bemor ma'lumotlari ---
    full_name = models.CharField(max_length=255)

    GENDER_CHOICES = [('M', _('Erkak')), ('F', _('Ayol'))]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)

    birth_date = models.DateField()

    # --- Rezidentlik ---
    RESIDENT_CHOICES = [
        ('resident', _('Rezident')),
        ('non_resident', _('Norezident')),
    ]
    resident_status = models.CharField(
        max_length=15,
        choices=RESIDENT_CHOICES,
        default='resident'
    )

    # --- Bemor kategoriyasi ---
    PATIENT_CATEGORY_CHOICES = [
        ('railway', _("Temir yo'lchi")),
        ('paid', _('Pullik')),
        ('non_resident', _('Norezident')),
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
        verbose_name=_("Bemor kategoriyasi")
    )

    # --- Kontakt ---
    phone = models.CharField(max_length=20, blank=True, verbose_name=_("Telefon raqami"))
    JSHSHIR = models.CharField(max_length=14, blank=True, verbose_name=_("JSHSHIR"))

    # --- Manzil ---
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey(District, on_delete=models.SET_NULL, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True)
    village = models.ForeignKey(Village, on_delete=models.SET_NULL, null=True, blank=True)
    street_address = models.CharField(max_length=255, blank=True)

    # --- Ijtimoiy holat ---
    SOCIAL_STATUS_CHOICES = [
        ('employed', _('Ishlaydi')),
        ('unemployed', _('Vaqtincha ishsiz')),
        ('pensioner', _('Pensioner')),
        ('student_higher', _('Student')),
        ('student_school', _("O'quvchi")),
        ('dependent', _("Ota-ona qaramog'ida")),
    ]
    social_status = models.CharField(max_length=20, choices=SOCIAL_STATUS_CHOICES, blank=True)
    workplace = models.CharField(max_length=255, blank=True, verbose_name=_("Ish joyi / O'quv joyi"))
    parent_name = models.CharField(max_length=255, blank=True, verbose_name=_("Ota-ona / Vasiy ismi"))
    parent_jshshir = models.CharField(max_length=14, blank=True, verbose_name=_("Ota-ona JSHSHIR"))
    parent_workplace_org = models.ForeignKey(
        'Organization', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children_patients', verbose_name=_("Ota-ona ish joyi")
    )
    workplace_org = models.ForeignKey(
        Organization,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='employees',
        verbose_name=_("Ish joyi (ro'yxatdan)")
    )
    position = models.CharField(max_length=255, blank=True, verbose_name=_("Lavozimi"))

    # --- Passport ---
    passport_serial = models.CharField(max_length=20, blank=True)

    # --- Kim olib kelgan ---
    REFERRAL_TYPE_CHOICES = [
        ('self', _("O'zi kelgan")),
        ('ambulance', _('Tez tibbiy yordam')),
        ('referral', _("Yo'llanma orqali")),
        ('liniya', _("Liniya")),
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
        ('under_6', _('Dastlabki 6 soat ichida')),
        ('7_to_24', _('7-24 soat ichida')),
        ('over_24', _('24 soatdan keyin')),
    ]
    hours_after_illness = models.CharField(
        max_length=10, choices=HOURS_AFTER_ILLNESS_CHOICES, blank=True
    )

    # --- Qo'shimcha ---
    is_emergency = models.BooleanField(default=False)
    is_paid = models.BooleanField(default=False)
    is_pensioner = models.BooleanField(default=False, verbose_name=_("Pensioner"))
    # is_pensioner endi social_status='pensioner' dan avtomatik aniqlanadi
    # BooleanField qoldirildi (eski ma'lumotlar uchun)

    # --- Shifoxona turi ---
    hospital_type = models.ForeignKey(
        HospitalType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Shifoxona turi")
    )

    # --- Statsionar/Ambulator ---
    IS_AMBULATORY_CHOICES = [
        ('inpatient', _('Statsionar (yotqizilgan)')),
        ('ambulatory', _('Ambulator (kunlik)')),
    ]
    visit_type = models.CharField(
        max_length=15,
        choices=IS_AMBULATORY_CHOICES,
        default='inpatient',
        blank=True,
        verbose_name=_("Tashrif turi")
    )

    # --- Yotish ma'lumotlari ---
    room_number = models.CharField(max_length=20, blank=True, verbose_name=_("Xona raqami"))
    MOBILITY_TYPE_CHOICES = [
        ('walking',    _('Yura oladi')),
        ('wheelchair', _('Aravachada')),
        ('stretcher',  _('Zambilda')),
    ]
    mobility_type = models.CharField(
        max_length=15, choices=MOBILITY_TYPE_CHOICES, blank=True,
        verbose_name=_("Harakatlanish turi")
    )
    TRANSPORT_TYPE_CHOICES = [
        ('ambulance', _('Tez tibbiy yordam')),
        ('own',       _("O'z transporti")),
        ('police',    _('Politsiya')),
        ('other',     _('Boshqa')),
    ]
    transport_type = models.CharField(
        max_length=15, choices=TRANSPORT_TYPE_CHOICES, blank=True,
        verbose_name=_("Transport turi")
    )

    # --- Tibbiy ko'rsatkichlar ---
    BLOOD_GROUP_CHOICES = [
        ('I',   _('I (0)')),
        ('II',  _('II (A)')),
        ('III', _('III (B)')),
        ('IV',  _('IV (AB)')),
    ]
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True,
        verbose_name=_("Qon guruhi")
    )
    RH_FACTOR_CHOICES = [
        ('pos', _('Rh+ (musbat)')),
        ('neg', _('Rh− (manfiy)')),
    ]
    rh_factor = models.CharField(
        max_length=5, choices=RH_FACTOR_CHOICES, blank=True,
        verbose_name=_("Rezus-faktor")
    )
    drug_allergy    = models.TextField(blank=True, verbose_name=_("Dorilarga allergiya"))
    height_cm       = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name=_("Bo'yi (sm)"))
    weight_kg       = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True, verbose_name=_("Vazni (kg)"))
    body_temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True, verbose_name=_("Harorat (°C)"))

    # --- Yotqizilgan ---
    admission_date = models.DateTimeField()
    department = models.ForeignKey(
        Department, on_delete=models.SET_NULL, null=True,
        related_name='admissions'
    )

    # --- Qayta yotqizilish ---
    ADMISSION_COUNT_CHOICES = [
        ('first', _('Birinchi marta')),
        ('repeated', _('Qayta')),
    ]
    admission_count = models.CharField(
        max_length=10, choices=ADMISSION_COUNT_CHOICES, blank=True
    )

    # --- Necha kun ---
    days_in_hospital = models.PositiveIntegerField(default=0)

    # --- Chiqish ---
    OUTCOME_CHOICES = [
        ('discharged', _('Chiqarildi')),
        ('deceased', _('Vafot etdi')),
        ('transferred', _("Boshqa shifoxonaga o'tkazildi")),
    ]
    outcome = models.CharField(max_length=15, choices=OUTCOME_CHOICES, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    discharge_conclusion = models.ForeignKey(
        DischargeConclusion, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Chiqish xulosasi")
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
        'users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='attending_cards'
    )
    # Registratsiyada tanlangan davolovchi shifokor faqat ma'lumot sifatida saqlanadi.
    # Bu flag faqat bo'lim mudiri tomonidan rasmiy biriktirish amalga oshirilganda True bo'ladi.
    attending_doctor_confirmed = models.BooleanField(
        default=False,
        verbose_name=_("Davolovchi shifokor tasdiqlangan")
    )
    department_head = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True,
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
        verbose_name = _("Bemor kartasi")
        verbose_name_plural = _("Bemor kartalari")
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
        verbose_name = _("O'lim sababi")
        verbose_name_plural = _("O'lim sabablari")


# --- Jarrohlik amaliyotlari ---
class SurgicalOperation(models.Model):
    patient_card = models.ForeignKey(
        PatientCard, on_delete=models.CASCADE, related_name='operations'
    )
    operation_date = models.DateField(null=True, blank=True)
    operation_type = models.ForeignKey(
        OperationType, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_("Amaliyot turi")
    )
    operation_name = models.CharField(max_length=255, blank=True)
    ANESTHESIA_CHOICES = [
        ('yes', _('Narkoz bilan')),
        ('no', _('Narkozsiz')),
        ('local', _('Mahalliy narkoz')),
    ]
    anesthesia = models.CharField(max_length=10, choices=ANESTHESIA_CHOICES, blank=True)
    complication = models.TextField(blank=True)

    def __str__(self):
        name = self.operation_type or self.operation_name
        return f"{name} ({self.operation_date})"

    class Meta:
        verbose_name = _("Jarrohlik amaliyoti")
        verbose_name_plural = _("Jarrohlik amaliyotlari")


# --- MKB-10 ---
class ICD10Code(models.Model):
    code = models.CharField(max_length=10, unique=True)
    title_uz = models.CharField(max_length=500)
    title_ru = models.CharField(max_length=500, blank=True)
    category = models.CharField(max_length=5, blank=True)

    class Meta:
        ordering = ['code']
        verbose_name = _("MKB-10 kodi")
        verbose_name_plural = _("MKB-10 kodlari")

    def __str__(self):
        return f"{self.code} — {self.title_uz}"

class DepartmentTransfer(models.Model):
    """Bemor bo'limlar orasidagi ko'chirish tarixi"""
    patient_card = models.ForeignKey(
        PatientCard,
        on_delete=models.CASCADE,
        related_name='transfers',
        verbose_name=_("Bemor kartasi")
    )
    from_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='transfers_from',
        verbose_name=_("Qayerdan")
    )
    to_department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        related_name='transfers_to',
        verbose_name=_("Qayerga")
    )
    transferred_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Ko'chirish sanasi")
    )
    transferred_by = models.ForeignKey(
        'users.CustomUser',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name=_("Kim ko'chirgan")
    )
    reason = models.TextField(blank=True, verbose_name=_("Sabab"))

    class Meta:
        verbose_name = _("Bo'lim ko'chirish")
        verbose_name_plural = _("Bo'lim ko'chirishlar")
        ordering = ['-transferred_at']

    def __str__(self):
        return f"{self.patient_card} → {self.to_department}"

# apps/patients/models.py ga qo'shish — oxiriga

# apps/patients/models.py ga qo'shish — oxiriga

class PatientTransfer(models.Model):
    """Bemor ko'chirish tarixi"""

    patient_card = models.ForeignKey(
        'PatientCard', on_delete=models.CASCADE,
        related_name='patient_transfers', verbose_name=_("Bemor")
    )
    from_department = models.ForeignKey(
        'Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_from',
        verbose_name=_("Avvalgi bo'lim")
    )
    from_doctor = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_from_doctor',
        verbose_name=_("Avvalgi shifokor")
    )
    from_dept_head = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_from_head',
        verbose_name=_("Avvalgi bo'lim mudiri")
    )
    to_department = models.ForeignKey(
        'Department', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_to',
        verbose_name=_("Yangi bo'lim")
    )
    to_doctor = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_to_doctor',
        verbose_name=_("Yangi shifokor")
    )
    to_dept_head = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='patient_transfers_to_head',
        verbose_name=_("Yangi bo'lim mudiri")
    )
    reason = models.TextField(blank=True, verbose_name=_("Sabab / izoh"))
    transfer_date = models.DateField(null=True, blank=True, verbose_name=_("Ko'chirish sanasi"))
    transferred_by = models.ForeignKey(
        'users.CustomUser', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name=_("Kim ko'chirdi")
    )
    transferred_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yaratilgan vaqt"))

    class Meta:
        verbose_name        = _("Ko'chirish tarixi")
        verbose_name_plural = _("Ko'chirish tarixi")
        ordering            = ['transferred_at']

    def __str__(self):
        return f"{self.patient_card} → {self.to_department} ({self.transferred_at.strftime('%d.%m.%Y')})"


# ==================== TIBBIY KO'RIK (BARCHA TURLAR) ====================

class MedicalExamination(models.Model):
    EXAM_TYPE_CHOICES = [
        ('initial',          _("Dastlabki ko'rik")),
        ('ward',             _("Bo'limda tekshirish")),
        ('daily',            _('Tekshirish kundaligi')),
        ('specialist',       _('Maxsus mutaxassis tekshirishi')),
        ('clinical_basis',   _('Klinik tashxisning asoslanishi')),
        ('stage_epicrisis',  _('Bosqichli epikriz')),
        ('discharge',        _('Chiqarish epikrizi')),
        ('consilium',        _('Statsionar sharoitidagi Konsilium')),
        ('anesthesia',       _("Anesteziologning jarrohlik amaliyotidan oldingi ko'rigi")),
    ]

    patient_card      = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='medical_examinations')
    examination_type  = models.CharField(max_length=30, choices=EXAM_TYPE_CHOICES, verbose_name=_("Ko'rik turi"))
    examination_datetime = models.DateTimeField(null=True, blank=True, verbose_name=_("Ko'rik vaqti"))
    created_by        = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='medical_examinations', verbose_name=_("Qo'shgan foydalanuvchi"))

    department_head_name     = models.CharField(max_length=255, blank=True, verbose_name=_("Bo'lim mudiri"))
    complaints               = models.TextField(blank=True, verbose_name=_("Shikoyatlar"))
    anamnesis_morbi          = models.TextField(blank=True, verbose_name=_("Kasallik tarixi"))
    anamnesis_vitae          = models.TextField(blank=True, verbose_name=_("Hayot tarixi"))
    status_localis           = models.TextField(blank=True, verbose_name=_("Mahalliy holat"))
    epidemiological_anamnesis = models.TextField(blank=True, verbose_name=_("Epidemiologik anamnez"))
    status_praesens          = models.TextField(blank=True, verbose_name=_("Hozirgi holat"))
    allergy_anamnesis        = models.TextField(blank=True, verbose_name=_("Allergologik anamnez"))
    neurological_status      = models.TextField(blank=True, verbose_name=_("Nevrologik holat"))
    lab_investigations       = models.TextField(blank=True, verbose_name=_("Lab tekshiruvlari"))
    selected_lab_tests   = models.ManyToManyField('LabTestAssignment', blank=True, related_name='cited_in_examinations', verbose_name=_("Tanlangan laboratoriya natijalari"))
    selected_diagnostics = models.ManyToManyField('DiagnosticAssignment', blank=True, related_name='cited_in_examinations', verbose_name=_("Tanlangan diagnostika natijalari"))
    specialist_consultations = models.TextField(blank=True, verbose_name=_("Turdosh mutaxassislar maslahatlari"))
    conclusion               = models.TextField(blank=True, verbose_name=_("Xulosa / Tavsiya"))
    drug_justification       = models.TextField(blank=True, verbose_name=_("Dori vositalari uchun asoslar"))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Tibbiy ko'rik")
        verbose_name_plural = _("Tibbiy ko'riklar")
        ordering            = ['-examination_datetime', '-created_at']

    def __str__(self):
        return f"{self.get_examination_type_display()} — {self.patient_card}"


# ==================== AMBULATOR QABUL ====================

class AmbulatoryConsultation(models.Model):
    STATUS_CHOICES = [
        ('in_progress', _('Davom etmoqda')),
        ('completed',   _('Yakunlandi')),
    ]

    patient_card = models.OneToOneField(PatientCard, on_delete=models.CASCADE, related_name='ambulatory_consultation')
    doctor       = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='ambulatory_consultations')

    result         = models.TextField(blank=True, verbose_name=_("Qabul natijasi"))
    recommendation = models.TextField(blank=True, verbose_name=_("Tavsiyalar"))
    conclusion     = models.TextField(blank=True, verbose_name=_("Xulosa"))

    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='in_progress', verbose_name=_("Holati"))
    started_at  = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Ambulator qabul")
        verbose_name_plural  = _("Ambulator qabullar")

    def __str__(self):
        return f"Ambulator qabul — {self.patient_card}"


class DoctorTextTemplate(models.Model):
    KIND_CHOICES = [
        ('result',                    _('Qabul natijasi')),
        ('recommendation',            _('Tavsiyalar')),
        ('conclusion',                _('Xulosa')),
        ('complaints',                _('Shikoyatlar')),
        ('anamnesis_morbi',           _('Kasallik tarixi (Anamnesis morbi)')),
        ('epidemiological_anamnesis', _('Epidemiologik anamnez')),
        ('anamnesis_vitae',           _('Hayot anamnezi (Anamnesis vitae)')),
        ('status_praesens',           _("Ob'ektiv holat (Status praesens)")),
        ('neurological_status',       _('Nevrologik holat')),
        ('status_localis',            _('Mahalliy holat (Status localis)')),
        ('lab_investigations',        _('Laboratoriya va instrumental tadqiqotlar')),
        ('allergy_anamnesis',         _('Allergoanamnesis')),
        ('drug_justification',        _('Dori vositalari uchun asoslar')),
    ]

    doctor = models.ForeignKey('users.CustomUser', on_delete=models.CASCADE, null=True, blank=True, related_name='text_templates')
    kind   = models.CharField(max_length=32, choices=KIND_CHOICES, verbose_name=_("Turi"))
    title  = models.CharField(max_length=150, verbose_name=_("Nomi"))
    body   = models.TextField(verbose_name=_("Matn"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _("Shifokor shabloni")
        verbose_name_plural = _("Shifokor shablonlari")
        ordering            = ['kind', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_kind_display()})"


# ==================== BOSHLANG'ICH KO'RIK ====================

class InitialExamination(models.Model):
    patient_card             = models.OneToOneField(PatientCard, on_delete=models.CASCADE, related_name='initial_examination')
    complaints               = models.TextField(blank=True, verbose_name=_("Shikoyatlar"))
    anamnesis_morbi          = models.TextField(blank=True, verbose_name=_("Kasallik tarixi (Anamnesis morbi)"))
    anamnesis_vitae          = models.TextField(blank=True, verbose_name=_("Hayot tarixi (Anamnesis vitae)"))
    status_localis           = models.TextField(blank=True, verbose_name=_("Mahalliy holat (Status localis)"))
    epidemiological_anamnesis = models.TextField(blank=True, verbose_name=_("Epidemiologik anamnez"))
    status_praesens          = models.TextField(blank=True, verbose_name=_("Hozirgi holat (Status praesens)"))
    allergy_anamnesis        = models.TextField(blank=True, verbose_name=_("Allergologik anamnez"))
    neurological_status      = models.TextField(blank=True, verbose_name=_("Nevrologik holat"))
    lab_investigations       = models.TextField(blank=True, verbose_name=_("Laboratoriya tekshiruvlari"))
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Boshlang'ich ko'rik")
        verbose_name_plural = _("Boshlang'ich ko'riklar")

    def __str__(self):
        return f"Ko'rik: {self.patient_card}"


# ==================== EPIZOD TASHXISLARI ====================

class EpisodeDiagnosis(models.Model):
    DIAGNOSIS_TYPE_CHOICES = [
        ('preliminary', _('Dastlabki')),
        ('final',       _('Yakuniy')),
    ]
    DIAGNOSIS_ROLE_CHOICES = [
        ('main',         _('Asosiy')),
        ('comorbidity',  _('Hamroh kasallik')),
        ('complication', _('Asorat')),
        ('background',   _('Fon kasalligi')),
        ('competitive',  _('Raqobatdosh')),
    ]
    DISEASE_COURSE_CHOICES = [
        ('',               _('Belgilanmagan')),
        ('acute',          _("O'tkir")),
        ('subacute',       _("O'tkir osti")),
        ('chronic_first',  _("Hayotda birinchi marta surunkali")),
        ('chronic_year',   _("Bu yil birinchi marta surunkali")),
        ('chronic',        _('Surunkali')),
    ]

    patient_card   = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='episode_diagnoses')
    icd10_code     = models.ForeignKey(ICD10Code, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_("MKB-10 kodi"))
    diagnosis_type = models.CharField(max_length=15, choices=DIAGNOSIS_TYPE_CHOICES, default='preliminary', verbose_name=_("Tashxis turi"))
    diagnosis_role = models.CharField(max_length=15, choices=DIAGNOSIS_ROLE_CHOICES, default='main', verbose_name=_("Tashxis roli"))
    disease_course = models.CharField(max_length=20, choices=DISEASE_COURSE_CHOICES, blank=True, verbose_name=_("Kasallikning kechishi"))
    clinical_text  = models.TextField(blank=True, verbose_name=_("Klinik matn"), max_length=3000)
    sort_order     = models.PositiveSmallIntegerField(default=0)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _("Epizod tashxisi")
        verbose_name_plural = _("Epizod tashxislari")
        ordering            = ['sort_order', 'created_at']

    def __str__(self):
        code = self.icd10_code.code if self.icd10_code else '—'
        return f"{code} ({self.get_diagnosis_role_display()})"


# ==================== SHIFOKOR BILDIRISHNOMALARI ====================

class DoctorNotification(models.Model):
    recipient = models.ForeignKey(
        'users.CustomUser', on_delete=models.CASCADE,
        related_name='doctor_notifications', verbose_name=_("Qabul qiluvchi")
    )
    patient_card = models.ForeignKey(
        PatientCard, on_delete=models.CASCADE,
        related_name='doctor_notifications', null=True, blank=True
    )
    message = models.CharField(max_length=255, verbose_name=_("Xabar"))
    is_read = models.BooleanField(default=False, verbose_name=_("O'qilgan"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _("Shifokor bildirishnomasi")
        verbose_name_plural = _("Shifokor bildirishnomalari")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.recipient}: {self.message}"


# ==================== DAVOLASH JARAYONI — TIBBIY MUOLAJALAR ====================

class TreatmentProcedure(models.Model):
    SOURCE_CHOICES = [
        ('patient_brought', _('Bemor tomonidan olib kelingan')),
        ('clinic_stock',    _('Klinika omboridan')),
    ]
    STATUS_CHOICES = [
        ('assigned',    _('Tayinlangan')),
        ('in_progress', _('Jarayonda')),
        ('done',        _('Bajarilgan')),
        ('cancelled',   _('Bekor qilingan')),
    ]

    patient_card  = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='treatment_procedures', verbose_name=_("Bemor kartasi"))
    assigned_by   = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_procedures', verbose_name=_("Tayinlagan shifokor"))
    service       = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='treatment_procedures', verbose_name=_("Xizmat (katalogdan)"))
    patient_service = models.OneToOneField('services.PatientService', on_delete=models.SET_NULL, null=True, blank=True, related_name='treatment_procedure', verbose_name=_("Hisob-faktura yozuvi"))

    medicine_name   = models.CharField(max_length=255, verbose_name=_("Dori vositasi nomi"))
    dosage          = models.CharField(max_length=100, blank=True, verbose_name=_("Dori dozasi"))
    quantity        = models.PositiveIntegerField(default=1, verbose_name=_("Muolaja soni"))
    schedule_note   = models.CharField(max_length=255, blank=True, verbose_name=_("Bajarish vaqti"))
    medicine_source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='clinic_stock', verbose_name=_("Dori manbasi"))
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='assigned', verbose_name=_("Holati"))
    notes           = models.TextField(blank=True, verbose_name=_("Izoh"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Tayinlangan sana"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Tibbiy muolaja")
        verbose_name_plural = _("Tibbiy muolajalar")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.medicine_name} — {self.patient_card}"


class ProcedureExecutionLog(models.Model):
    procedure    = models.ForeignKey(TreatmentProcedure, on_delete=models.CASCADE, related_name='execution_logs', verbose_name=_("Muolaja"))
    performed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_procedures', verbose_name=_("Bajaruvchi hamshira"))
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Bajarilgan vaqt"))
    comment      = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))

    class Meta:
        verbose_name        = _("Muolaja bajarilish logi")
        verbose_name_plural = _("Muolaja bajarilish loglari")
        ordering            = ['-performed_at']

    def __str__(self):
        return f"{self.procedure.medicine_name} — {self.performed_at:%d.%m.%Y %H:%M}"


# ==================== RETSEPT (Шифокор -> бемор) ====================

class Prescription(models.Model):
    FREQUENCY_UNIT_CHOICES = [
        ('День',    _('Kuniga')),
        ('Неделя',  _('Haftada')),
        ('Месяц',   _('Oyda')),
    ]

    patient_card  = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='prescriptions', verbose_name=_("Bemor kartasi"))
    doctor        = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions', verbose_name=_("Yozgan shifokor"))
    treatment_procedure = models.OneToOneField(TreatmentProcedure, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescription', verbose_name=_("Bog'langan muolaja (hamshira reja)"))

    drug_name      = models.CharField(max_length=255, verbose_name=_("Dori nomi"))
    dosage_form    = models.CharField(max_length=255, blank=True, verbose_name=_("Форма выпуска"))
    dose           = models.CharField(max_length=100, blank=True, verbose_name=_("Доза"))
    frequency_num  = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Частота приёма (son)"))
    frequency_unit = models.CharField(max_length=10, choices=FREQUENCY_UNIT_CHOICES, default='День', blank=True, verbose_name=_("Частота приёма (birlik)"))
    single_dose    = models.CharField(max_length=50, blank=True, verbose_name=_("Разовая доза"))
    method         = models.CharField(max_length=255, blank=True, verbose_name=_("Способ применения"))
    duration_days  = models.PositiveIntegerField(null=True, blank=True, verbose_name=_("Продолжительность приёма (kun)"))
    intake_time    = models.CharField(max_length=10, blank=True, verbose_name=_("Время приёма"))
    date_start     = models.DateField(null=True, blank=True, verbose_name=_("Davr boshi"))
    date_end       = models.DateField(null=True, blank=True, verbose_name=_("Davr oxiri"))
    total_quantity = models.CharField(max_length=50, blank=True, verbose_name=_("Kol-vo препарата"))
    note           = models.CharField(max_length=500, blank=True, verbose_name=_("Примечание"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yozilgan sana"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Retsept")
        verbose_name_plural = _("Retseptlar")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.drug_name} — {self.patient_card}"


# ==================== LABORATORIYA TAYINLASH (shifokor -> laborant) ====================

class LabTestAssignment(models.Model):
    STATUS_CHOICES = [
        ('assigned',     _('Tayinlangan')),
        ('sample_taken', _('Namuna olingan')),
        ('in_progress',  _('Tekshirilmoqda')),
        ('done',         _('Yakunlangan')),
        ('cancelled',    _('Bekor qilingan')),
    ]

    patient_card = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='lab_test_assignments', verbose_name=_("Bemor kartasi"))
    assigned_by  = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_lab_tests', verbose_name=_("Tayinlagan shifokor"))
    service      = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_test_assignments', verbose_name=_("Xizmat (katalogdan)"))
    patient_service = models.OneToOneField('services.PatientService', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_test_assignment', verbose_name=_("Hisob-faktura yozuvi"))

    test_name = models.CharField(max_length=255, verbose_name=_("Tahlil/tekshiruv nomi"))
    notes     = models.TextField(blank=True, verbose_name=_("Klinik ko'rsatma / izoh"))
    status    = models.CharField(max_length=15, choices=STATUS_CHOICES, default='assigned', verbose_name=_("Holati"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Tayinlangan sana"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Laboratoriya tahlili")
        verbose_name_plural = _("Laboratoriya tahlillari")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.test_name} — {self.patient_card}"


class LabTestResultLog(models.Model):
    assignment   = models.ForeignKey(LabTestAssignment, on_delete=models.CASCADE, related_name='result_logs', verbose_name=_("Tahlil"))
    performed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_lab_tests', verbose_name=_("Bajaruvchi laborant"))
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Bajarilgan vaqt"))
    result_text  = models.TextField(blank=True, verbose_name=_("Natija / xulosa"))
    recommendation = models.TextField(blank=True, verbose_name=_("Tavsiya"))
    comment      = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))

    class Meta:
        verbose_name        = _("Tahlil natijasi logi")
        verbose_name_plural = _("Tahlil natijalari loglari")
        ordering            = ['-performed_at']

    def __str__(self):
        return f"{self.assignment.test_name} — {self.performed_at:%d.%m.%Y %H:%M}"


# ==================== DIAGNOSTIKA TAYINLASH ====================

class DiagnosticAssignment(models.Model):
    TYPE_CHOICES = [
        ('uzi',         _('UZI')),
        ('rentgen',     _('Rentgen')),
        ('mrt',         _('MRT')),
        ('kt',          _('KT')),
        ('ekg',         _('EKG')),
        ('endoskopiya', _('Endoskopiya')),
        ('other',       _('Boshqa')),
    ]
    STATUS_CHOICES = [
        ('assigned',    _('Tayinlangan')),
        ('in_progress', _('Bajarilmoqda')),
        ('done',        _('Tayyor')),
        ('cancelled',   _('Bekor qilingan')),
    ]

    patient_card = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='diagnostic_assignments', verbose_name=_("Bemor kartasi"))
    assigned_by  = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_diagnostics', verbose_name=_("Tayinlagan shifokor"))
    service      = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='diagnostic_assignments', verbose_name=_("Xizmat (katalogdan)"))
    patient_service = models.OneToOneField('services.PatientService', on_delete=models.SET_NULL, null=True, blank=True, related_name='diagnostic_assignment', verbose_name=_("Hisob-faktura yozuvi"))

    diagnostic_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_("Tekshiruv turi"))
    notes           = models.TextField(blank=True, verbose_name=_("Klinik ko'rsatma / izoh"))
    status          = models.CharField(max_length=15, choices=STATUS_CHOICES, default='assigned', verbose_name=_("Holati"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Tayinlangan sana"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Diagnostika tekshiruvi")
        verbose_name_plural = _("Diagnostika tekshiruvlari")
        ordering            = ['-created_at']

    def __str__(self):
        return f"{self.get_diagnostic_type_display()} — {self.patient_card}"


class DiagnosticResultLog(models.Model):
    assignment   = models.ForeignKey(DiagnosticAssignment, on_delete=models.CASCADE, related_name='result_logs', verbose_name=_("Tekshiruv"))
    performed_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_diagnostics', verbose_name=_("Bajaruvchi"))
    performed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Bajarilgan vaqt"))
    conclusion   = models.TextField(blank=True, verbose_name=_("Xulosa"))
    recommendation = models.TextField(blank=True, verbose_name=_("Tavsiya"))
    comment      = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))

    class Meta:
        verbose_name        = _("Diagnostika natijasi logi")
        verbose_name_plural = _("Diagnostika natijalari loglari")
        ordering            = ['-performed_at']

    def __str__(self):
        return f"{self.assignment} — {self.performed_at:%d.%m.%Y %H:%M}"


# ==================== KONSULTATSIYALAR ====================

class ConsultationRequest(models.Model):
    SPECIALTY_CHOICES = [
        ('neurology',      _('Nevrologiya')),
        ('cardiology',     _('Kardiologiya')),
        ('therapy',        _('Terapiya')),
        ('surgery',        _('Jarrohlik')),
        ('endocrinology',  _('Endokrinologiya')),
        ('consilium',      _('Konsilium')),
    ]
    STATUS_CHOICES = [
        ('assigned',    _('Yuborilgan')),
        ('in_progress', _("Ko'rib chiqilmoqda")),
        ('done',        _('Javob berilgan')),
        ('cancelled',   _('Bekor qilingan')),
    ]

    patient_card = models.ForeignKey(PatientCard, on_delete=models.CASCADE, related_name='consultation_requests', verbose_name=_("Bemor kartasi"))
    requested_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='requested_consultations', verbose_name=_("So'rov yuborgan shifokor"))
    consultants  = models.ManyToManyField('users.CustomUser', blank=True, related_name='consultation_invites', verbose_name=_("Taklif qilingan mutaxassislar"))
    service      = models.ForeignKey('services.Service', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_requests', verbose_name=_("Konsultatsiya xizmati (katalogdan)"))
    patient_service = models.OneToOneField('services.PatientService', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_request', verbose_name=_("Hisob-faktura yozuvi"))

    specialty = models.CharField(max_length=20, choices=SPECIALTY_CHOICES, blank=True, verbose_name=_("Yo'nalish"))
    reason    = models.TextField(blank=True, verbose_name=_("So'rov sababi / klinik savol"))
    status    = models.CharField(max_length=15, choices=STATUS_CHOICES, default='assigned', verbose_name=_("Holati"))
    cancel_reason = models.TextField(blank=True, verbose_name=_("Bekor qilish sababi"))

    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Yuborilgan sana"))
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = _("Konsultatsiya so'rovi")
        verbose_name_plural = _("Konsultatsiya so'rovlari")
        ordering            = ['-created_at']

    @property
    def display_label(self):
        if self.service_id:
            return self.service.name
        return self.get_specialty_display()

    def __str__(self):
        return f"{self.display_label} — {self.patient_card}"


class ConsultationResponse(models.Model):
    request      = models.ForeignKey(ConsultationRequest, on_delete=models.CASCADE, related_name='responses', verbose_name=_("So'rov"))
    responded_by = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation_responses', verbose_name=_("Javob bergan mutaxassis"))
    responded_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Javob vaqti"))
    conclusion   = models.TextField(verbose_name=_("Xulosa / tavsiya"))
    comment      = models.CharField(max_length=500, blank=True, verbose_name=_("Izoh"))

    class Meta:
        verbose_name        = _("Konsultatsiya javobi")
        verbose_name_plural = _("Konsultatsiya javoblari")
        ordering            = ['-responded_at']

    def __str__(self):
        return f"{self.request} — {self.responded_at:%d.%m.%Y %H:%M}"


# ==================== REJALASHTIRISH — MUOLAJA/TAHLIL/DIAGNOSTIKA/KONSULTATSIYA VAQTI ====================

class ServiceSchedule(models.Model):
    """Shifokor tayinlagan xizmatning bajarilishi rejalashtirilgan vaqti — bitta band = bitta qator
    (ko'p kunlik kurs uchun har kuniga bitta qator yaratiladi). Aynan bitta target maydon to'ldiriladi."""
    STATUS_CHOICES = [
        ('pending',   _('Kutilmoqda')),
        ('done',      _('Bajarildi')),
        ('missed',    _("O'tkazib yuborildi")),
        ('cancelled', _('Bekor qilindi')),
        ('stopped',   _("To'xtatildi")),
    ]

    treatment_procedure   = models.ForeignKey(TreatmentProcedure, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_occurrences', verbose_name=_("Muolaja"))
    lab_test_assignment   = models.ForeignKey(LabTestAssignment, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_occurrences', verbose_name=_("Laboratoriya tahlili"))
    diagnostic_assignment = models.ForeignKey(DiagnosticAssignment, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_occurrences', verbose_name=_("Diagnostika tekshiruvi"))
    consultation_request  = models.ForeignKey(ConsultationRequest, on_delete=models.CASCADE, null=True, blank=True, related_name='schedule_occurrences', verbose_name=_("Konsultatsiya so'rovi"))

    scheduled_at     = models.DateTimeField(db_index=True, verbose_name=_("Rejalashtirilgan vaqt"))
    status           = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending', verbose_name=_("Holati"))
    completed_at     = models.DateTimeField(null=True, blank=True, verbose_name=_("Bajarilgan vaqt"))
    performed_by     = models.ForeignKey('users.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='completed_schedule_occurrences', verbose_name=_("Bajaruvchi"))
    reminder_sent_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Eslatma yuborilgan vaqt"))
    reason           = models.TextField(blank=True, verbose_name=_("Bekor qilish/to'xtatish sababi"))
    comment          = models.TextField(blank=True, verbose_name=_("Izoh (nojo'ya ta'sirlar)"))
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = _("Xizmat rejasi")
        verbose_name_plural = _("Xizmat rejalari")
        ordering            = ['scheduled_at']
        indexes = [models.Index(fields=['status', 'reminder_sent_at', 'scheduled_at'])]
        constraints = [models.CheckConstraint(
            condition=(
                models.Q(treatment_procedure__isnull=False, lab_test_assignment__isnull=True, diagnostic_assignment__isnull=True, consultation_request__isnull=True) |
                models.Q(treatment_procedure__isnull=True, lab_test_assignment__isnull=False, diagnostic_assignment__isnull=True, consultation_request__isnull=True) |
                models.Q(treatment_procedure__isnull=True, lab_test_assignment__isnull=True, diagnostic_assignment__isnull=False, consultation_request__isnull=True) |
                models.Q(treatment_procedure__isnull=True, lab_test_assignment__isnull=True, diagnostic_assignment__isnull=True, consultation_request__isnull=False)
            ),
            name='servicesched_exactly_one_target',
        )]

    @property
    def target(self):
        return self.treatment_procedure or self.lab_test_assignment or self.diagnostic_assignment or self.consultation_request

    @property
    def patient_card(self):
        t = self.target
        return t.patient_card if t else None

    @property
    def label(self):
        if self.treatment_procedure_id:
            return f"💉 {self.treatment_procedure.medicine_name}"
        if self.lab_test_assignment_id:
            return f"🧪 {self.lab_test_assignment.test_name}"
        if self.diagnostic_assignment_id:
            return f"🩻 {self.diagnostic_assignment.get_diagnostic_type_display()}"
        if self.consultation_request_id:
            return f"🩺 {self.consultation_request.display_label}"
        return ''

    def __str__(self):
        return f"{self.label} — {self.scheduled_at:%d.%m.%Y %H:%M}"
