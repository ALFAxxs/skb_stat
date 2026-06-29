# apps/care/permissions.py

from rest_framework.permissions import BasePermission


class IsDoctorOrAdmin(BasePermission):
    """Yo'llanma / dori-muolaja tayinlash — faqat shifokor yoki admin."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role in ('doctor', 'admin')))


class IsNurseOrAdmin(BasePermission):
    """Hamshira vazifalari va favqulodda holat — faqat hamshira yoki admin."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_superuser or user.role in ('nurse', 'admin')))


class IsDeptHeadOrAdmin(BasePermission):
    """Bo'lim mudiri (CustomUser.is_head) yoki admin."""

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or user.role == 'admin':
            return True
        return user.role in ('doctor', 'old') and user.is_head and user.is_active


def scope_to_user_departments(qs, user, path='patient_card__department_id'):
    """Admin/statistician/reception uchun cheklovsiz; boshqalar uchun
    foydalanuvchining bo'lim(lar)i bilan filtrlaydi."""
    if user.is_superuser or user.role in ('admin', 'statistician', 'reception'):
        return qs
    dept_ids = user.get_all_department_ids()
    if dept_ids:
        return qs.filter(**{f"{path}__in": dept_ids})
    return qs.none()
