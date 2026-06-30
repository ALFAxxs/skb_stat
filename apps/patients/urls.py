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

    # --- Shifokor kabineti ---
    path('doctor/', views.doctor_dashboard, name='doctor_dashboard'),
    path('doctor/statsionar/', views.doctor_patient_list, {'visit_type': 'inpatient'}, name='doctor_inpatients'),
    path('doctor/ambulator/', views.doctor_patient_list, {'visit_type': 'ambulatory'}, name='doctor_outpatients'),
    path('doctor/biriktirish/', views.doctor_assign_patients, name='doctor_assign_patients'),
    path('doctor/bemor/<int:pk>/', views.doctor_patient_card, name='doctor_patient_card'),
    path('doctor/ajax/notifications/', views.doctor_notifications_ajax, name='doctor_notifications_ajax'),
    path('doctor/ajax/notifications/read/', views.doctor_notifications_read, name='doctor_notifications_read'),
    path('reja/<int:pk>/holat/', views.schedule_occurrence_update, name='schedule_occurrence_update'),
    path('doctor/bemor/<int:pk>/muolaja/tayinlash/', views.procedure_assign, name='procedure_assign'),
    path('doctor/bemor/<int:pk>/tahlil/tayinlash/', views.lab_test_assign, name='lab_test_assign'),
    path('doctor/bemor/<int:pk>/diagnostika/tayinlash/', views.diagnostic_assign, name='diagnostic_assign'),
    path('doctor/bemor/<int:pk>/yozuv-qoshish/', views.assign_services, name='assign_services'),
    path('doctor/bemor/<int:pk>/konsultatsiya/sorov/', views.consultation_request_create, name='consultation_request_create'),
    path('doctor/konsultatsiya/<int:pk>/javob/', views.consultation_respond, name='consultation_respond'),
    path('doctor/konsultatsiya/<int:pk>/holat/', views.consultation_update_status, name='consultation_update_status'),
    path('doctor/konsultatsiya/<int:pk>/boshlash/', views.consultation_start, name='consultation_start'),
    path('doctor/konsultatsiya/<int:pk>/bekor/', views.consultation_cancel, name='consultation_cancel'),
    path('doctor/konsultatsiyalar/', views.doctor_consultation_inbox, name='doctor_consultation_inbox'),
    path('doctor/bemor/<int:patient_id>/ambulator-qabul/', views.ambulatory_consultation_form, name='ambulatory_consultation_form'),
    path('doctor/ambulator-qabul/<int:pk>/saqlash/', views.ambulatory_consultation_save, name='ambulatory_consultation_save'),
    path('doctor/ambulator-qabul/<int:pk>/chop-etish/', views.ambulatory_consultation_print, name='ambulatory_consultation_print'),
    path('doctor/shablon/qoshish/', views.doctor_template_create, name='doctor_template_create'),
    path('doctor/bemor/<int:pk>/retsept/qoshish/', views.prescription_add, name='prescription_add'),
    path('retsept/<int:pk>/yangilash/', views.prescription_update, name='prescription_update'),
    path('retsept/<int:pk>/ochirish/', views.prescription_delete, name='prescription_delete'),
    path('retsept/<int:pk>/chop-etish/', views.prescription_print, name='prescription_print'),

    # --- Hamshira kabineti ---
    path('hamshira/', views.nurse_dashboard, name='nurse_dashboard'),
    path('hamshira/muolaja/<int:pk>/bajarish/', views.procedure_log_execution, name='procedure_log_execution'),
    path('hamshira/muolaja/<int:pk>/holat/', views.procedure_update_status, name='procedure_update_status'),

    # --- Laborant — shifokor tayinlagan tahlillar navbati ---
    path('laboratoriya/tayinlovlar/', views.lab_assignment_queue, name='lab_assignment_queue'),
    path('laboratoriya/tayinlov/<int:pk>/natija/', views.lab_test_result_form, name='lab_test_result_form'),
    path('laboratoriya/tayinlov/<int:pk>/natija/saqlash/', views.lab_test_result_save, name='lab_test_result_save'),
    path('laboratoriya/tayinlov/<int:pk>/chop-etish/', views.lab_test_result_print, name='lab_test_result_print'),
    path('laboratoriya/tayinlov/<int:pk>/holat/', views.lab_test_update_status, name='lab_test_update_status'),

    # --- Diagnost kabineti ---
    path('diagnostika/', views.diagnostic_queue, name='diagnostic_queue'),
    path('diagnostika/<int:pk>/natija/', views.diagnostic_result_form, name='diagnostic_result_form'),
    path('diagnostika/<int:pk>/natija/saqlash/', views.diagnostic_result_save, name='diagnostic_result_save'),
    path('diagnostika/<int:pk>/chop-etish/', views.diagnostic_result_print, name='diagnostic_result_print'),
    path('diagnostika/<int:pk>/holat/', views.diagnostic_update_status, name='diagnostic_update_status'),



    # --- AJAX URL lar ---
    path('icd10/search/', views.icd10_search, name='icd10_search'),
    path('ajax/icd10-search/', views.icd10_search, name='icd10_search_ajax'),
    path('ajax/episode-diagnoses/<int:patient_id>/', views.episode_diagnoses, name='episode_diagnoses'),
    path('ajax/medical-examinations/<int:patient_id>/', views.medical_examinations_list, name='medical_examinations_list'),
    path('ajax/medical-examination/<int:pk>/delete/', views.medical_examination_delete, name='medical_examination_delete'),
    path('<int:patient_id>/examination/new/', views.medical_examination_page, name='examination_new'),
    path('<int:patient_id>/examination/<int:exam_pk>/edit/', views.medical_examination_page, name='examination_edit'),
    path('<int:patient_id>/examination/<int:exam_pk>/chop-etish/', views.medical_examination_print, name='examination_print'),
    path('<int:patient_id>/examination/chop-etish/oldindan/', views.medical_examination_print_preview, name='examination_print_preview'),
    path('ajax/episode-diagnosis/<int:pk>/delete/', views.episode_diagnosis_delete, name='episode_diagnosis_delete'),
    path('ajax/initial-examination/<int:patient_id>/', views.initial_examination, name='initial_examination'),
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
    path('<int:pk>/excel/', views.patient_card_excel, name='patient_card_excel'),
    path('<int:pk>/invoice/', views.patient_invoice, name='patient_invoice'),
    path('<int:pk>/transfer/', views.patient_transfer, name='patient_transfer'),
    path('maktub/', views.sevgi_maktubi, name='sevgi_maktubi'),
]