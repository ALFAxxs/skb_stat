# apps/patients/forms.py

import re
from django import forms
from django.core.exceptions import ValidationError
from .models import PatientCard, DeathCause, SurgicalOperation


# ==================== VALIDATORS ====================

def validate_passport(value):
    if not value:
        return value
    pattern = r'^[A-Z]{2}\d{7}$'
    if not re.match(pattern, value.upper()):
        raise ValidationError("Passport seriyasi noto'g'ri format. To'g'ri format: AA1234567")
    return value.upper()


def validate_mkb10(value):
    if not value:
        return value
    pattern = r'^[A-Z]\d{2}(\.\d{1,2})?$'
    if not re.match(pattern, value.upper()):
        raise ValidationError("MKB-10 kodi noto'g'ri. To'g'ri format: A00 yoki A00.0")
    return value.upper()


# ==================== ASOSIY FORMA ====================

class PatientCardForm(forms.ModelForm):

    passport_serial = forms.CharField(
        max_length=20,
        required=False,
        validators=[validate_passport],
        widget=forms.TextInput(attrs={'placeholder': 'AA1234567'}),
        label="Passport seriyasi"
    )

    clinical_main_diagnosis = forms.CharField(
        required=False,
        validators=[validate_mkb10],
        widget=forms.TextInput(attrs={'placeholder': 'A00.0'}),
        label="Klinik asosiy tashxis (MKB-10)"
    )

    pathological_main_diagnosis = forms.CharField(
        required=False,
        validators=[validate_mkb10],
        widget=forms.TextInput(attrs={'placeholder': 'A00.0'}),
        label="Patologoanatomik tashxis (MKB-10)"
    )

    is_emergency = forms.ChoiceField(
        choices=[(True, 'Ha'), (False, "Yo'q")],
        widget=forms.RadioSelect,
        label="Shoshilinch olib kelinganmi",
        required=False
    )

    is_paid = forms.ChoiceField(
        choices=[(True, 'Ha'), (False, "Yo'q")],
        widget=forms.RadioSelect,
        label="Pullik yotqizilganmi",
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Majburiy maydonlar
        self.fields['attending_doctor'].required = True
        self.fields['department_head'].required = True

        # Qolganlar...
        if 'status' in self.fields:
            self.fields['status'].required = False
            self.fields['status'].widget = forms.HiddenInput()
        if 'registered_by' in self.fields:
            self.fields['registered_by'].required = False
            self.fields['registered_by'].widget = forms.HiddenInput()
        if 'patient_category' in self.fields:
            self.fields['patient_category'].required = False
    class Meta:
        model = PatientCard
        fields = '__all__'
        widgets = {
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'admission_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'discharge_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'resident_status': forms.RadioSelect,
            'aids_test_date': forms.DateInput(attrs={'type': 'date'}),
            'wp_test_date': forms.DateInput(attrs={'type': 'date'}),
            'referring_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'admission_diagnosis': forms.Textarea(attrs={'rows': 2}),
            'clinical_main_diagnosis_text': forms.Textarea(attrs={'rows': 2}),
            'clinical_comorbidities': forms.Textarea(attrs={'rows': 2}),
            'pathological_main_diagnosis_text': forms.Textarea(attrs={'rows': 2}),
            'pathological_comorbidities': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'medical_record_number': 'Tibbiy bayonnoma raqami',
            'full_name': "To'liq ism-familiya",
            'resident_status': 'Rezidentlik holati',
            'patient_category': 'Bemor kategoriyasi',
            'gender': 'Jinsi',
            'birth_date': "Tug'ilgan sana",
            'phone': 'Telefon raqami',
            'JSHSHIR': 'JSHSHIR',
            'social_status': 'Ijtimoiy holati',
            'workplace': "Ish joyi / O'quv joyi",
            'position': 'Lavozimi',
            'country': 'Davlat',
            'region': 'Viloyat',
            'district': 'Tuman',
            'city': 'Shahar',
            'village': 'Qishloq',
            'street_address': "Ko'cha nomi va uy raqami",
            'referral_type': 'Kim tomonidan olib kelingan',
            'referral_organization': "Yo'llagan muassasa",
            'referring_diagnosis': "Yo'llagan muassasa tashxisi",
            'admission_diagnosis': "Qabul bo'limi tashxisi",
            'hours_after_illness': 'Kasallanishdan necha soat keyin',
            'hospital_type': 'Shifoxona turi',
            'admission_date': 'Yotqizilgan sana va soat',
            'department': "Qaysi bo'limga yotqizildi",
            'admission_count': 'Yotqizilish holati',
            'days_in_hospital': 'Shifoxonada yotgan kunlar soni',
            'outcome': 'Kasallanish yakuni',
            'discharge_conclusion': 'Chiqish xulosasi',
            'discharge_date': 'Chiqgan/Vafot etgan sana',
            'aids_test_date': 'OITS tekshiruvi sanasi',
            'aids_test_result': 'OITS natijasi',
            'wp_test_date': 'WP tekshiruvi sanasi',
            'wp_test_result': 'WP natijasi',
            'is_war_veteran': 'Nogironlik urush qatnashchisimi',
            'attending_doctor': 'Davolovchi shifokor',
            'department_head': "Bo'lim mudiri",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bu maydonlar formda ko'rsatilmaydi — required=False va initial bor
        if 'status' in self.fields:
            self.fields['status'].required = False
            self.fields['status'].widget = forms.HiddenInput()  # ← yashirin

        if 'patient_category' in self.fields:
            self.fields['patient_category'].required = False
            # Formda ko'rsatiladi yoki yashirin

        if 'registered_by' in self.fields:
            self.fields['registered_by'].required = False
            self.fields['registered_by'].widget = forms.HiddenInput()

    def clean_is_emergency(self):
        value = self.cleaned_data.get('is_emergency')
        if not value:
            return False
        return value == 'True' or value is True

    def clean_is_paid(self):
        value = self.cleaned_data.get('is_paid')
        if not value:
            return False
        return value == 'True' or value is True

    def clean_is_war_veteran(self):
        value = self.cleaned_data.get('is_war_veteran')
        if isinstance(value, bool):
            return value
        return str(value) == 'True'

    def clean_is_pensioner(self):
        value = self.cleaned_data.get('is_pensioner')
        if isinstance(value, bool):
            return value
        return str(value) == 'True'

    def clean_passport_serial(self):
        return self.cleaned_data.get('passport_serial', '').upper()

    def clean(self):
        cleaned_data = super().clean()
        resident_status = cleaned_data.get('resident_status')
        outcome = cleaned_data.get('outcome')
        discharge_date = cleaned_data.get('discharge_date')
        referral_type = cleaned_data.get('referral_type')
        referral_org = cleaned_data.get('referral_organization')

        # Default qiymatlar — formda ko'rsatilmagan maydonlar
        if not cleaned_data.get('status'):
            cleaned_data['status'] = self.instance.status if self.instance.pk else 'registered'
        if not cleaned_data.get('patient_category'):
            cleaned_data['patient_category'] = (
                self.instance.patient_category if self.instance.pk else 'railway'
            )

        # Norezident bo'lsa — passport majburiy emas
        if resident_status == 'non_resident':
            cleaned_data['passport_serial'] = cleaned_data.get('passport_serial') or 'NOREZIDENT'
            if 'passport_serial' in self._errors:
                del self._errors['passport_serial']

        # Chiqish sanasi majburiy
        if outcome and not discharge_date:
            self.add_error('discharge_date', "Chiqish/vafot sanasini kiriting.")

        # Yo'llanma yoki Liniya bo'lsa — muassasa majburiy
        if referral_type in ('referral', 'liniya') and not referral_org:
            self.add_error('referral_organization', "Yo'llagan muassasani tanlang.")

        # Vafot bo'lmasa — patologoanatomik maydonlar tozalanadi
        if outcome != 'deceased':
            cleaned_data['pathological_main_diagnosis'] = ''
            cleaned_data['pathological_main_diagnosis_text'] = ''
            cleaned_data['pathological_comorbidities'] = ''

        return cleaned_data


# ==================== O'LIM SABABI FORMASI ====================

class DeathCauseForm(forms.ModelForm):
    class Meta:
        model = DeathCause
        exclude = ['patient_card']
        widgets = {
            'immediate_cause': forms.Textarea(attrs={'rows': 2}),
            'underlying_cause': forms.Textarea(attrs={'rows': 2}),
            'other_significant_conditions': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'immediate_cause': "a) O'limga olib kelgan bevosita sabab",
            'underlying_cause': "b) O'lim sababini bevosita chaqiruvchi kasallik",
            'main_disease_code': 'v) Asosiy kasallik kodi (MKB-10)',
            'other_significant_conditions': "Bog'liq bo'lmagan boshqa muhim kasalliklar",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.required = False

    def clean_main_disease_code(self):
        return validate_mkb10(self.cleaned_data.get('main_disease_code', ''))


# ==================== QABULXONA FORMASI ====================

class ReceptionForm(forms.ModelForm):
    """Qabulxona uchun soddalashtirilgan forma"""

    is_emergency = forms.ChoiceField(
        choices=[(True, 'Ha'), (False, "Yo'q")],
        widget=forms.RadioSelect,
        label="Shoshilinch olib kelinganmi",
        required=False
    )
    is_paid = forms.ChoiceField(
        choices=[(True, 'Ha'), (False, "Yo'q")],
        widget=forms.RadioSelect,
        label="Pullik yotqizilganmi",
        required=False
    )

    class Meta:
        model = PatientCard
        fields = [
            'admission_date', 'full_name', 'birth_date', 'gender',
            'admission_diagnosis', 'department', 'patient_category',
            'social_status', 'passport_serial', 'JSHSHIR', 'phone',
            'resident_status', 'country', 'region', 'district', 'city',
            'street_address', 'workplace', 'position', 'hospital_type',
            'referral_type', 'referral_organization', 'hours_after_illness',
            'is_emergency', 'is_paid',
            'is_war_veteran', 'is_pensioner',
            'attending_doctor',
            'department_head',
        ]
        widgets = {
            'admission_date': forms.DateTimeInput(
                attrs={'type': 'datetime-local'},
                format='%Y-%m-%dT%H:%M'
            ),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
            'resident_status': forms.RadioSelect,
            'admission_diagnosis': forms.Textarea(attrs={'rows': 2}),
        }
        labels = {
            'admission_date': 'Kelgan sana va soat',
            'full_name': "To'liq ism-familiya",
            'birth_date': "Tug'ilgan sana",
            'gender': 'Jinsi',
            'admission_diagnosis': 'Qabulxona tashxisi',
            'department': "Yotqizilgan bo'lim",
            'patient_category': 'Bemor kategoriyasi',
            'social_status': 'Ijtimoiy holati',
            'passport_serial': 'Passport seriyasi',
            'JSHSHIR': 'JSHSHIR',
            'phone': 'Telefon raqami',
            'resident_status': 'Rezidentlik holati',
            'country': 'Davlat',
            'region': 'Viloyat',
            'district': 'Tuman',
            'city': 'Shahar',
            'street_address': "Ko'cha va uy raqami",
            'workplace': "Ish joyi / O'quv joyi",
            'position': 'Lavozimi',
            'hospital_type': 'Shifoxona turi',
            'referral_type': 'Kim tomonidan keltirilgan',
            'referral_organization': "Yo'llagan muassasa",
            'hours_after_illness': 'Kasallanishdan necha soat keyin',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from .models import Doctor, Department, HospitalType

        self.fields['hospital_type'].queryset = HospitalType.objects.filter(is_active=True)
        self.fields['hospital_type'].empty_label = "— Tanlang —"
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['department'].empty_label = "— Tanlang —"

        # Shifokorlar — majburiy emas
        self.fields['attending_doctor'].required = False
        self.fields['attending_doctor'].empty_label = "— Tanlang —"
        self.fields['department_head'].required = False
        self.fields['department_head'].empty_label = "— Tanlang —"

        required_fields = [
            'admission_date', 'full_name', 'birth_date',
            'gender', 'admission_diagnosis', 'department',
            'patient_category', 'social_status'
        ]
        for field in self.fields:
            if field not in required_fields:
                self.fields[field].required = False

    def clean_is_emergency(self):
        value = self.cleaned_data.get('is_emergency')
        if not value:
            return False
        return value == 'True' or value is True

    def clean_is_paid(self):
        value = self.cleaned_data.get('is_paid')
        if not value:
            return False
        return value == 'True' or value is True

    def clean_is_war_veteran(self):
        value = self.cleaned_data.get('is_war_veteran')
        if isinstance(value, bool):
            return value
        return str(value) == 'True'

    def clean_is_pensioner(self):
        value = self.cleaned_data.get('is_pensioner')
        if isinstance(value, bool):
            return value
        return str(value) == 'True'

    def clean_passport_serial(self):
        return self.cleaned_data.get('passport_serial', '').upper()


# ==================== JARROHLIK FORMASI ====================

class SurgicalOperationForm(forms.ModelForm):
    class Meta:
        model = SurgicalOperation
        exclude = ['patient_card']
        widgets = {
            'operation_date': forms.DateInput(attrs={'type': 'date'}),
            'complication': forms.Textarea(attrs={'rows': 2}),
            'operation_name': forms.TextInput(attrs={
                'placeholder': "Qo'lda kiriting yoki yuqoridan tanlang"
            }),
        }
        labels = {
            'operation_date': 'Amaliyot sanasi',
            'operation_type': 'Amaliyot turi (bazadan)',
            'operation_name': "Amaliyot nomi (qo'lda)",
            'anesthesia': 'Narkoz',
            'complication': 'Asorati',
        }


# ==================== INLINE FORMSET ====================

SurgicalOperationFormSet = forms.inlineformset_factory(
    PatientCard,
    SurgicalOperation,
    form=SurgicalOperationForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)