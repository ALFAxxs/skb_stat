# apps/services/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Bemor xizmatlari
    path('patient/<int:patient_pk>/', views.patient_services, name='patient_services'),
    path('patient/<int:patient_pk>/add/', views.add_service, name='add_service'),
    path('<int:pk>/update/', views.update_service, name='update_service'),
    path('<int:pk>/delete/', views.delete_service, name='delete_service'),

    # AJAX
    path('search/', views.service_search, name='service_search'),

    # Statistika
    path('statistics/', views.statistics_combined, name='service_statistics'),
    path('statistics/old/', views.service_statistics, name='service_statistics_old'),

    # Dori-darmon
    path('medicine/search/', views.medicine_search, name='medicine_search'),
    path('patient/<int:patient_pk>/medicine/add/', views.add_medicine, name='add_medicine'),
    path('medicine/<int:pk>/update/', views.update_medicine, name='update_medicine'),
    path('medicine/<int:pk>/delete/', views.delete_medicine, name='delete_medicine'),

    # Dori statistikasi
    path('medicine/statistics/', views.medicine_statistics, name='medicine_statistics'),
    path('medicine/export/excel/', views.export_medicine_excel, name='export_medicine_excel'),

    # Operatsiya statistikasi
    path('operations/statistics/', views.operation_statistics, name='operation_statistics'),
    path('operations/export/excel/', views.export_operation_excel, name='export_operation_excel'),

    # Operatsiya xizmatlari statistikasi
    path('operations/service-statistics/', views.operation_service_statistics, name='operation_service_statistics'),
    path('operations/service-statistics/excel/', views.export_operation_service_excel, name='export_operation_service_excel'),

    # Operatsiya belgilash
    path('mark-operations/', views.mark_operations, name='mark_operations'),

    # Export
    path('export/excel/', views.export_services_excel, name='export_services_excel'),
    path('export/pdf/', views.export_services_pdf, name='export_services_pdf'),
]