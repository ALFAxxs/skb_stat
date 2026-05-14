# apps/results/urls.py

from django.urls import path
from apps.results import views

urlpatterns = [
    # Shablonlar
    path('templates/',              views.template_list,   name='result_template_list'),
    path('templates/create/',       views.template_create, name='result_template_create'),
    path('templates/<int:pk>/edit/', views.template_edit,  name='result_template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='result_template_delete'),
    path('templates/<int:pk>/get/', views.template_get,    name='result_template_get'),

    # Natijalar
    path('create/<int:service_pk>/', views.result_create, name='result_create'),
    path('<int:pk>/edit/',           views.result_edit,   name='result_edit'),
    path('<int:pk>/',                views.result_view,   name='result_view'),
    path('<int:pk>/print/',          views.result_print,  name='result_print'),
]
