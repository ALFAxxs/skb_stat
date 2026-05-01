# apps/services/forms.py

from django import forms
from .models import PatientService, Service, ServiceCategory


class PatientServiceForm(forms.ModelForm):
    class Meta:
        model = PatientService
        fields = ['service', 'quantity', 'ordered_by', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
            'quantity': forms.NumberInput(attrs={'min': 1, 'value': 1}),
        }
        labels = {
            'service': 'Xizmat',
            'quantity': 'Miqdori',
            'ordered_by': 'Buyurtma bergan shifokor',
            'notes': 'Izoh',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = Service.objects.filter(
            is_active=True
        ).select_related('category').order_by('category__name', 'name')
        self.fields['ordered_by'].required = False
        self.fields['notes'].required = False


class ServiceResultForm(forms.ModelForm):
    class Meta:
        model = PatientService
        fields = ['status', 'result', 'performed_by', 'is_paid']
        widgets = {
            'result': forms.Textarea(attrs={'rows': 3}),
        }
        labels = {
            'status': 'Holat',
            'result': 'Natija / Xulosa',
            'performed_by': 'Bajargan shifokor',
            'is_paid': "To'langan",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.required = False
