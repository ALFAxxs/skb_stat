# apps/users/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'get_full_name', 'role', 'department', 'phone', 'is_active']
    list_filter = ['role', 'department', 'is_active']
    search_fields = ['username', 'first_name', 'last_name', 'phone']

    fieldsets = UserAdmin.fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('role', 'department', 'phone')
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Qo'shimcha ma'lumotlar", {
            'fields': ('role', 'department', 'phone')
        }),
    )

    # get_full_name ustun nomi
    admin.short_description = "Ism-familiya"