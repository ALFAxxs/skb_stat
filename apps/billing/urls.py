# apps/billing/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('patient/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('patient/<int:pk>/print/', views.invoice_print, name='invoice_print'),
    path('patient/<int:pk>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('patient/<int:pk>/payment/', views.record_payment, name='record_payment'),
    path('patient/<int:pk>/discount/', views.add_discount, name='add_discount'),
    path('patient/<int:pk>/refund/', views.add_refund, name='add_refund'),
    path('patient/<int:pk>/consumable/add/', views.add_consumable, name='add_consumable'),
    path('consumable/<int:pk>/delete/', views.delete_consumable, name='delete_consumable'),
    path('patient/<int:pk>/recalculate/', views.recalculate, name='recalculate_invoice'),
]
