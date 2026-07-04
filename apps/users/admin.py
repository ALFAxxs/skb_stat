# apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.urls import reverse
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ['username', 'get_full_name', 'role', 'get_departments', 'phone',
                     'is_head', 'is_general_practitioner', 'is_active', 'change_password_link']
    list_filter   = ['role', 'departments', 'is_head', 'is_general_practitioner', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'phone']

    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('role', 'department', 'departments', 'phone', 'is_head', 'is_general_practitioner')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('role', 'department', 'departments', 'phone', 'is_head', 'is_general_practitioner')
        }),
    )

    @admin.display(description="Bo'limlar")
    def get_departments(self, obj):
        return ", ".join(obj.departments.values_list('name', flat=True)) or "—"

    @admin.display(description="Parol")
    def change_password_link(self, obj):
        url = reverse('admin:users_customuser_password_change', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}">🔑 Parol o\'zgartirish</a>', url
        )
