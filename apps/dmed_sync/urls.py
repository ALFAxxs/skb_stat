from django.urls import path
from . import views

urlpatterns = [
    path('',              views.monitor,          name='dmed_monitor'),
    path('status.json',   views.status_json,      name='dmed_status_json'),
    path('run-now/',      views.run_now,           name='dmed_run_now'),
    path('retry-all/',    views.retry_all_failed,  name='dmed_retry_all'),
    path('<int:pk>/retry/', views.retry_record,    name='dmed_retry_record'),

    # Web-based DMED Login
    path('login/',                   views.dmed_login_page,   name='dmed_login_page'),
    path('login/start/',             views.dmed_login_start,  name='dmed_login_start'),
    path('login/<int:pk>/status/',   views.dmed_login_status, name='dmed_login_status'),
    path('login/<int:pk>/otp/',      views.dmed_login_otp,    name='dmed_login_otp'),
]
