# apps/users/decorators.py

from django.shortcuts import redirect
from functools import wraps


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in roles and not request.user.is_superuser:
                return redirect('access_denied')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def department_filter(queryset, user):
    if user.is_superuser or user.role in ('admin', 'reception', 'statistician'):
        return queryset
    dept_ids = user.get_all_department_ids()
    if dept_ids:
        return queryset.filter(department_id__in=dept_ids)
    return queryset.none()