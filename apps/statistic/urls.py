# apps/statistic/urls.py
from django.urls import path
from . import views
from .exports import export_excel, export_pdf
from .report_export import export_full_report
from .monthly_report import export_monthly_report

urlpatterns = [
    path('', views.statistics_dashboard, name='statistics_dashboard'),
    path('export/excel/', export_excel, name='export_excel'),
    path('export/pdf/', export_pdf, name='export_pdf'),
    path('export/full/', export_full_report, name='export_full_report'),
    path('export/monthly/', export_monthly_report, name='export_monthly_report'),
]
