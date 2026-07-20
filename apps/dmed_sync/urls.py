from django.urls import path
from . import views

urlpatterns = [
    path('',              views.monitor,          name='dmed_monitor'),
    path('status.json',   views.status_json,      name='dmed_status_json'),
    path('run-now/',      views.run_now,           name='dmed_run_now'),
    path('retry-all/',    views.retry_all_failed,  name='dmed_retry_all'),
    path('<int:pk>/retry/', views.retry_record,    name='dmed_retry_record'),
]
