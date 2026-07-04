
from django.urls import path
from . import views
from . import panel_views as pv

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/parol/', views.user_change_password, name='user_change_password'),
    path('users/<int:pk>/toggle/', views.user_toggle, name='user_toggle'),
    path('access-denied/', views.access_denied, name='access_denied'),

    # ─── Admin panel ───────────────────────────────────────────────
    path('panel/',                                    pv.panel_dashboard,           name='panel_dashboard'),

    # Bo'limlar
    path('panel/bolimlar/',                           pv.panel_departments,          name='panel_departments'),
    path('panel/bolimlar/saqlash/',                   pv.panel_department_save,      name='panel_department_save'),
    path('panel/bolimlar/<int:pk>/saqlash/',          pv.panel_department_save,      name='panel_department_edit'),
    path('panel/bolimlar/<int:pk>/toggle/',           pv.panel_department_toggle,    name='panel_department_toggle'),
    path('panel/bolimlar/<int:pk>/ochir/',            pv.panel_department_delete,    name='panel_department_delete'),

    # Xizmat kategoriyalari
    path('panel/kategoriyalar/',                      pv.panel_categories,           name='panel_categories'),
    path('panel/kategoriyalar/saqlash/',              pv.panel_category_save,        name='panel_category_save'),
    path('panel/kategoriyalar/<int:pk>/saqlash/',     pv.panel_category_save,        name='panel_category_edit'),
    path('panel/kategoriyalar/<int:pk>/ochir/',       pv.panel_category_delete,      name='panel_category_delete'),

    # Xizmatlar
    path('panel/xizmatlar/',                          pv.panel_services,             name='panel_services'),
    path('panel/xizmatlar/saqlash/',                  pv.panel_service_save,         name='panel_service_save'),
    path('panel/xizmatlar/<int:pk>/saqlash/',         pv.panel_service_save,         name='panel_service_edit'),
    path('panel/xizmatlar/<int:pk>/toggle/',          pv.panel_service_toggle,       name='panel_service_toggle'),
    path('panel/xizmatlar/<int:pk>/ochir/',           pv.panel_service_delete,       name='panel_service_delete'),

    # Dorilar
    path('panel/dorilar/',                            pv.panel_medicines,            name='panel_medicines'),
    path('panel/dorilar/saqlash/',                    pv.panel_medicine_save,        name='panel_medicine_save'),
    path('panel/dorilar/<int:pk>/saqlash/',           pv.panel_medicine_save,        name='panel_medicine_edit'),
    path('panel/dorilar/<int:pk>/toggle/',            pv.panel_medicine_toggle,      name='panel_medicine_toggle'),
    path('panel/dorilar/<int:pk>/ochir/',             pv.panel_medicine_delete,      name='panel_medicine_delete'),

    # Lab shablonlari
    path('panel/lab-shablonlar/',                     pv.panel_lab_templates,        name='panel_lab_templates'),
    path('panel/lab-shablonlar/saqlash/',             pv.panel_lab_template_save,    name='panel_lab_template_save'),
    path('panel/lab-shablonlar/<int:pk>/saqlash/',    pv.panel_lab_template_save,    name='panel_lab_template_edit'),
    path('panel/lab-shablonlar/<int:pk>/toggle/',     pv.panel_lab_template_toggle,  name='panel_lab_template_toggle'),
    path('panel/lab-shablonlar/<int:pk>/ochir/',      pv.panel_lab_template_delete,  name='panel_lab_template_delete'),
]
