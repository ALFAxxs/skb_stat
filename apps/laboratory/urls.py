# apps/laboratory/urls.py

from django.urls import path

from .views import (
    lab_home,
    lab_item_set_template,
    lab_item_transition,
    lab_parameter_add,
    lab_parameter_delete,
    lab_patient,
    lab_result_create,
    lab_result_enter,
    lab_result_pdf_download,
    lab_result_pdf_public,
    lab_result_print,
    lab_result_save,
    lab_template_create,
    lab_template_detail,
    lab_template_list,
)

urlpatterns = [
    # ── Dashboard ────────────────────────────────────────
    path('', lab_home, name='lab_home'),

    # ── Patient ──────────────────────────────────────────
    path('patient/<int:pk>/', lab_patient, name='lab_patient'),
    path('patient/<int:patient_pk>/create/', lab_result_create, name='lab_result_create'),

    # ── Order Items (status transitions) ─────────────────
    path('item/<int:pk>/transition/', lab_item_transition, name='lab_item_transition'),
    path('item/<int:pk>/set-template/', lab_item_set_template, name='lab_item_set_template'),

    # ── Results ──────────────────────────────────────────
    path('result/<int:pk>/enter/', lab_result_enter, name='lab_result_enter'),
    path('result/<int:pk>/save/', lab_result_save, name='lab_result_save'),
    path('result/<int:pk>/print/', lab_result_print, name='lab_result_print'),
    path('result/<int:pk>/pdf/', lab_result_pdf_download, name='lab_result_pdf_download'),
    path('result/pdf/<str:token>/', lab_result_pdf_public, name='lab_result_pdf_public'),

    # ── Templates ────────────────────────────────────────
    path('templates/', lab_template_list, name='lab_template_list'),
    path('templates/create/', lab_template_create, name='lab_template_create'),
    path('templates/<int:pk>/', lab_template_detail, name='lab_template_detail'),
    path('templates/<int:template_pk>/parameter/add/', lab_parameter_add, name='lab_parameter_add'),
    path('parameter/<int:pk>/delete/', lab_parameter_delete, name='lab_parameter_delete'),
]
