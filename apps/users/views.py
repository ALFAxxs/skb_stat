# apps/users/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib import messages
from django import forms as django_forms  # ← django forms
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .forms import LoginForm, CustomUserCreationForm  # ← foydalanuvchi formlari
from .models import CustomUser
from .decorators import role_required


def login_view(request):
    if request.user.is_authenticated:
        return redirect('patient_list')
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Xush kelibsiz, {user.get_full_name()}!")
        return redirect(request.GET.get('next', 'patient_list'))
    return render(request, 'users/login.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
@role_required('admin')
def user_list(request):
    users = CustomUser.objects.select_related('department').order_by('role', 'last_name')
    return render(request, 'users/user_list.html', {'users': users})


@login_required
@role_required('admin')
def user_create(request):
    form = CustomUserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Foydalanuvchi yaratildi.")
        return redirect('user_list')
    return render(request, 'users/user_form.html', {
        'form': form,
        'title': "Yangi foydalanuvchi"
    })


@login_required
@role_required('admin')
def user_edit(request, pk):
    user = get_object_or_404(CustomUser, pk=pk)

    class EditForm(django_forms.ModelForm):  # ← django_forms ishlatiladi
        class Meta:
            model = CustomUser
            fields = ['username', 'first_name', 'last_name',
                      'email', 'role', 'department', 'phone']

    form = EditForm(request.POST or None, instance=user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, "Foydalanuvchi yangilandi.")
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
        status = "faollashtirildi" if user.is_active else "bloklandi"
        messages.success(request, f"{user.get_full_name()} {status}.")
    return redirect('user_list')


def access_denied(request):
    return render(request, 'users/access_denied.html', status=403)