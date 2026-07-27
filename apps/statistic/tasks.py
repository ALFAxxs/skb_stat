# apps/statistic/tasks.py — Celery autodiscovery uchun re-export
from .export_tasks import (
    generate_patients_excel,
    generate_full_report_excel,
    generate_monthly_report_excel,
)

__all__ = [
    'generate_patients_excel',
    'generate_full_report_excel',
    'generate_monthly_report_excel',
]
