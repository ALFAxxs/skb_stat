# apps/care/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('referrals', views.ReferralViewSet, basename='referral')
router.register('medication-orders', views.MedicationOrderViewSet, basename='medication-order')
router.register('tasks', views.NurseTaskViewSet, basename='nurse-task')
router.register('emergencies', views.EmergencyEventViewSet, basename='emergency-event')
router.register('notifications', views.NotificationViewSet, basename='notification')
router.register('audit-logs', views.AuditLogViewSet, basename='audit-log')

urlpatterns = [
    path('dashboard/', views.DashboardView.as_view(), name='care-dashboard'),
    path('doctors/', views.DoctorListView.as_view(), name='care-doctors'),
    path('patients/<int:pk>/overview/', views.PatientCareOverviewView.as_view(), name='care-patient-overview'),
    path('', include(router.urls)),
]
