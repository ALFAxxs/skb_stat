# apps/statistic/export_tasks.py
import os
import uuid

from celery import shared_task
from django.conf import settings


def _export_dir():
    d = os.path.join(settings.MEDIA_ROOT, 'temp_exports')
    os.makedirs(d, exist_ok=True)
    return d


@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=560,
             name='statistic.export_patients_excel')
def generate_patients_excel(self, filters: dict, user_id: int) -> str:
    """Bemorlar ro'yxati Excel faylini Celery'da yaratadi va faylnomni qaytaradi."""
    from apps.patients.models import PatientCard
    from apps.users.models import CustomUser
    from apps.users.decorators import department_filter
    from .exports import _base_patient_qs, _apply_patient_filters, _build_workbook

    user = CustomUser.objects.get(pk=user_id)

    # Asosiy queryset (department filtri + barcha filtrlar)
    qs = department_filter(_base_patient_qs(), user)
    qs = _apply_patient_filters(qs, filters)

    # Statistika queryseti (faqat yil va bo'lim bo'yicha)
    qs_stats = PatientCard.objects.all()
    if filters.get('year'):
        qs_stats = qs_stats.filter(admission_date__year=filters['year'])
    if filters.get('department'):
        qs_stats = qs_stats.filter(department_id=filters['department'])

    wb = _build_workbook(qs, qs_stats)

    filename = f'patients_{uuid.uuid4().hex[:12]}.xlsx'
    filepath = os.path.join(_export_dir(), filename)
    wb.save(filepath)
    return filename


@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=560,
             name='statistic.export_full_report_excel')
def generate_full_report_excel(self, filters: dict, user_id: int) -> str:
    """To'liq hisobot (8 sheet) Excel faylini Celery'da yaratadi."""
    from apps.users.models import CustomUser
    from apps.users.decorators import department_filter
    from .exports import _base_patient_qs, _apply_patient_filters
    from .report_export import _build_full_report_workbook, _filter_text_from_params

    user = CustomUser.objects.get(pk=user_id)
    qs = department_filter(_base_patient_qs(), user)
    qs = _apply_patient_filters(qs, filters)
    qs = qs.select_related(
        'department', 'attending_doctor', 'workplace_org',
        'region', 'district', 'parent_workplace_org'
    )
    filter_text = _filter_text_from_params(filters)
    wb = _build_full_report_workbook(qs, filter_text)

    filename = f'fullreport_{uuid.uuid4().hex[:12]}.xlsx'
    filepath = os.path.join(_export_dir(), filename)
    wb.save(filepath)
    return filename


@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=560,
             name='statistic.export_monthly_report_excel')
def generate_monthly_report_excel(self, filters: dict, year: int, month: int, user_id: int) -> str:
    """Oylik rasmiy hisobot Excel faylini Celery'da yaratadi."""
    from apps.users.models import CustomUser
    from apps.users.decorators import department_filter
    from .exports import _base_patient_qs, _apply_patient_filters
    from .monthly_report import _build_monthly_report_workbook

    user = CustomUser.objects.get(pk=user_id)
    qs = department_filter(_base_patient_qs(), user)
    qs = _apply_patient_filters(qs, filters)
    if not filters.get('year'):
        qs = qs.filter(admission_date__year=year)
    if not filters.get('month'):
        qs = qs.filter(admission_date__month=month)
    qs = qs.select_related(
        'department', 'attending_doctor', 'workplace_org',
        'region', 'district', 'discharge_conclusion'
    )
    wb = _build_monthly_report_workbook(qs, year, month)

    filename = f'monthly_{uuid.uuid4().hex[:12]}.xlsx'
    filepath = os.path.join(_export_dir(), filename)
    wb.save(filepath)
    return filename
