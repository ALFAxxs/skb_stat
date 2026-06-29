# conf/urls.py

from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('patient_list'), name='home'),
    path('patients/', include('apps.patients.urls')),
    path('statistics/', include('apps.statistic.urls')),
    path('services/', include('apps.services.urls')),
    path('', include('apps.users.urls')),  # login, logout, users, access-denied
    path('contracts/', include('apps.contracts.urls')),
    path('queue/', include('apps.queue_app.urls')),
    path('laboratory/', include('apps.laboratory.urls')),
    path('billing/', include('apps.billing.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
    path('api/bot/', include('apps.telegram_bot.urls')),
    path('api/care/', include('apps.care.urls')),
    path('api/auth/token/', obtain_auth_token, name='api-auth-token'),
]