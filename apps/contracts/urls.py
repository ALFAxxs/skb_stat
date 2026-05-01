# apps/contracts/urls.py

from django.urls import path
from apps.contracts import views

urlpatterns = [
    path('<int:pk>/download/', views.download_contract,        name='download_contract'),
    path('<int:pk>/regenerate/', views.regenerate_contract,    name='regenerate_contract'),
    path('verify/<uuid:token>/', views.verify_contract,        name='verify_contract'),
    path('verify/<uuid:token>/pdf/', views.download_contract_public, name='download_contract_public'),
]