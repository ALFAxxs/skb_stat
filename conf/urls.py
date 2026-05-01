# conf/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('patient_list'), name='home'),
    path('patients/', include('apps.patients.urls')),
    path('statistics/', include('apps.statistic.urls')),
    path('services/', include('apps.services.urls')),
    path('', include('apps.users.urls')),  # login, logout, users, access-denied
    path('contracts/', include('apps.contracts.urls')),
    path('queue/', include('apps.queue_app.urls')),
]