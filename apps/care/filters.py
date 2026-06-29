# apps/care/filters.py

import django_filters

from .models import AuditLog, EmergencyEvent, NurseTask, Referral


class NurseTaskFilter(django_filters.FilterSet):
    date = django_filters.DateFilter(field_name='scheduled_at', lookup_expr='date')
    date_from = django_filters.DateTimeFilter(field_name='scheduled_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='scheduled_at', lookup_expr='lte')
    department = django_filters.NumberFilter(field_name='patient_card__department_id')

    class Meta:
        model = NurseTask
        fields = ['status', 'task_type', 'patient_card', 'date', 'date_from', 'date_to', 'department']


class ReferralFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(field_name='patient_card__department_id')

    class Meta:
        model = Referral
        fields = ['service_type', 'priority', 'status', 'patient_card', 'department']


class EmergencyEventFilter(django_filters.FilterSet):
    department = django_filters.NumberFilter(field_name='department_id')

    class Meta:
        model = EmergencyEvent
        fields = ['status', 'event_type', 'patient_card', 'department']


class AuditLogFilter(django_filters.FilterSet):
    class Meta:
        model = AuditLog
        fields = ['patient_card', 'action']
