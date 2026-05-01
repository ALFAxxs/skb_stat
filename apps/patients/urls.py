# apps/patients/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # --- Oddiy URL lar avval ---
    path('', views.patient_list, name='patient_list'),
    path('create/', views.patient_card_create, name='patient_create'),
    path('operation-types/search/', views.operation_type_search, name='operation_type_search'),
    path('reception/', views.reception_create, name='reception_create'),
    path('ambulatory/', views.ambulatory_create, name='ambulatory_create'),



    # --- AJAX URL lar ---
    path('icd10/search/', views.icd10_search, name='icd10_search'),
    path('ajax/regions/', views.get_regions, name='get_regions'),
    path('ajax/districts/', views.get_districts, name='get_districts'),
    path('ajax/cities/', views.get_cities, name='get_cities'),
    path('ajax/villages/', views.get_villages, name='get_villages'),
    path('conclusion/add/', views.add_conclusion, name='add_conclusion'),
    path('ajax/doctors/', views.get_doctors, name='get_doctors'),
    path('ajax/organizations/', views.organization_search, name='organization_search'),
    path('ajax/check-patient/', views.check_existing_patient, name='check_existing_patient'),

    # --- pk li URL lar eng oxirda ---
    path('<int:pk>/', views.patient_detail, name='patient_detail'),
    path('<int:pk>/edit/', views.patient_card_edit, name='patient_edit'),
    path('<int:pk>/delete/', views.patient_delete, name='patient_delete'),
    path('<int:pk>/pdf/', views.patient_card_pdf, name='patient_card_pdf'),
    path('<int:pk>/excel/', views.patient_card_excel, name='patient_card_excel'),
    path('<int:pk>/invoice/', views.patient_invoice, name='patient_invoice'),
    path('<int:pk>/transfer/', views.transfer_department, name='transfer_department'),
]