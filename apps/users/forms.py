# apps/users/forms.py

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import CustomUser


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Login',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Parol',
            'class': 'form-control'
        })
    )


class CustomUserCreationForm(UserCreationForm):

    # password1 va password2 ga stil qo'shish
    password1 = forms.CharField(
        label="Parol",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parol kiriting'
        })
    )
    password2 = forms.CharField(
        label="Parolni tasdiqlang",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Parolni qayta kiriting'
        })
    )

    # Faqat role='doctor' bo'lganda ko'rinadi — Doctor profiliga ko'chiriladi
    is_department_head = forms.BooleanField(
        label="Bo'lim mudiri",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    class Meta:
        model = CustomUser
        fields = [
            'username', 'first_name', 'last_name',
            'email', 'role', 'department', 'departments', 'phone',
        ]
        widgets = {
            'username':   forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name':  forms.TextInput(attrs={'class': 'form-control'}),
            'email':      forms.EmailInput(attrs={'class': 'form-control'}),
            'role':       forms.Select(attrs={'class': 'form-select'}),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'departments': forms.CheckboxSelectMultiple(),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+998901234567'
            }),
        }
        labels = {
            'username':    'Login',
            'first_name':  'Ism',
            'last_name':   'Familiya',
            'email':       'Email',
            'role':        'Rol',
            'department':  'Asosiy bo\'lim',
            'departments': "Bo'limlar",
            'phone':       'Telefon',
        }

    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            _sync_doctor_profile(user, self.cleaned_data.get('is_department_head', False))
        return user


def _sync_doctor_profile(user, is_head):
    """role='doctor' bo'lsa — Doctor yozuvini yaratadi/yangilaydi va foydalanuvchiga bog'laydi."""
    from apps.patients.models import Doctor

    if user.role != 'doctor':
        return

    doctor = getattr(user, 'doctor_profile', None)
    if doctor is None:
        doctor = Doctor(user=user)
    doctor.full_name = user.get_full_name() or user.username
    doctor.department = user.department
    doctor.is_head = is_head
    doctor.is_active = user.is_active
    doctor.save()