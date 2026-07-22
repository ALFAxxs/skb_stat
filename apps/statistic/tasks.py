# apps/statistic/tasks.py — Celery autodiscovery uchun re-export
from .export_tasks import generate_patients_excel

__all__ = ['generate_patients_excel']
