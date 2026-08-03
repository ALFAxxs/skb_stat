from django.urls import path
from . import views

urlpatterns = [
    path('',                  views.monitor,          name='dmed_monitor'),
    path('status.json',       views.status_json,      name='dmed_status_json'),
    path('run-now/',          views.run_now,           name='dmed_run_now'),
    path('retry-all/',        views.retry_all_failed,  name='dmed_retry_all'),
    path('pause/',            views.toggle_pause,        name='dmed_toggle_pause'),
    path('reset-running/',    views.reset_running,       name='dmed_reset_running'),
    path('sync-selected/',    views.sync_selected,       name='dmed_sync_selected'),
    path('enqueue-patients/', views.enqueue_patients_page, name='dmed_enqueue_patients'),
    path('enqueue-patients/run/', views.enqueue_patients_run, name='dmed_enqueue_patients_run'),
    path('<int:pk>/retry/',   views.retry_record,      name='dmed_retry_record'),

    # Web-based DMED Login
    path('login/',                   views.dmed_login_page,   name='dmed_login_page'),
    path('login/start/',             views.dmed_login_start,  name='dmed_login_start'),
    path('login/<int:pk>/status/',   views.dmed_login_status, name='dmed_login_status'),
    path('login/<int:pk>/otp/',      views.dmed_login_otp,    name='dmed_login_otp'),
    path('login/import/',            views.dmed_session_import, name='dmed_session_import'),
]
