# apps/statistic/urls.py
from django.urls import path
from . import views
from .exports import export_excel
from .report_export import export_full_report
from .monthly_report import export_monthly_report

urlpatterns = [
    path('', views.statistics_dashboard, name='statistics_dashboard'),
    path('export/excel/', export_excel, name='export_excel'),
    path('export/excel/start/', views.export_patients_start, name='export_patients_start'),
    path('export/full/', export_full_report, name='export_full_report'),
    path('export/monthly/', export_monthly_report, name='export_monthly_report'),
]
