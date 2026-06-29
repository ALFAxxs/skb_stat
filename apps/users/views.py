# apps/users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django import forms as django_forms  # ← django forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from .forms import LoginForm, CustomUserCreationForm, _sync_doctor_profile  # ← foydalanuvchi formlari
from .models import CustomUser
from .decorators import role_required


def login_view(request):
    if request.user.is_authenticated:
        if request.user.role == 'laborant':
            return redirect('lab_home')
        if request.user.role == 'doctor':
            return redirect('doctor_dashboard')
        if request.user.role in ('nurse', 'head_nurse'):
            return redirect('nurse_dashboard')
        if request.user.role == 'diagnostician':
            return redirect('diagnostic_queue')
        return redirect('patient_list')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, _("Xush kelibsiz, %(name)s!") % {'name': user.get_full_name()})
        next_url = request.GET.get('next', '')
        if next_url:
            return redirect(next_url)
        if user.role == 'laborant':
            return redirect('lab_home')
        if user.role == 'doctor':
            return redirect('doctor_dashboard')
        if user.role in ('nurse', 'head_nurse'):
            return redirect('nurse_dashboard')
        if user.role == 'diagnostician':
            return redirect('diagnostic_queue')
        return redirect('patient_list')
    return render(request, 'users/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@role_required('admin')
def user_list(request):
    users = CustomUser.objects.prefetch_related('departments').order_by('role', 'last_name')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
@role_required('admin')
def user_create(request):
    form = CustomUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Foydalanuvchi yaratildi."))
        return redirect('user_list')
    return render(request, 'users/user_form.html', {
        'form': form,
        'title': "Yangi foydalanuvchi"
    })


@login_required
@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    class EditForm(django_forms.ModelForm):
        is_department_head = django_forms.BooleanField(
            label="Bo'lim mudiri",
            required=False,
            widget=django_forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        )

        class Meta:
            model = CustomUser
            fields = ['username', 'first_name', 'last_name',
                      'email', 'role', 'department', 'departments', 'phone']
            widgets = {
                'department': django_forms.Select(attrs={'class': 'form-select'}),
                'departments': django_forms.CheckboxSelectMultiple(),
            }
            labels = {'department': "Asosiy bo'lim"}

    doctor_profile = getattr(user, 'doctor_profile', None)
    initial = {'is_department_head': doctor_profile.is_head if doctor_profile else False}
    form = EditForm(request.POST or None, instance=user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        saved_user = form.save()
        _sync_doctor_profile(saved_user, form.cleaned_data.get('is_department_head', False))
        messages.success(request, _("Foydalanuvchi yangilandi."))
        return redirect('user_list')

    return render(request, 'users/user_form.html', {
        'form': form,
        'title': f"Tahrirlash: {user.get_full_name()}"
    })


@login_required
@role_required('admin')
def user_toggle(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)
    if user != request.user:
        user.is_active = not user.is_active
        user.save()
        status = _("faollashtirildi") if user.is_active else _("bloklandi")
        messages.success(request, _("%(name)s %(status)s.") % {'name': user.get_full_name(), 'status': status})
    return redirect('user_list')


def access_denied(request):
    return render(request, 'users/access_denied.html', status=403)