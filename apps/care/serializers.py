# apps/care/serializers.py

from rest_framework import serializers

from apps.patients.models import (
    ConsultationRequest, DiagnosticAssignment, LabTestAssignment,
)
from apps.users.models import CustomUser

from .models import (
    AuditLog, EmergencyEvent, MedicationOrder, NurseTask, Notification, Referral,
    TaskCompletionLog,
)
from .services import process_medication_order, process_referral, report_emergency


# ==================== DOCTOR (referral uchun tanlov ro'yxati) ====================

class DoctorSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)

    class Meta:
        model = CustomUser
        fields = ['id', 'full_name', 'department', 'department_name', 'is_head']


# ==================== REFERRAL ====================

class ReferralSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True)
    referring_doctor_name = serializers.CharField(source='referring_doctor.full_name', read_only=True, default=None)
    target_doctor_name = serializers.CharField(source='target_doctor.full_name', read_only=True, default=None)
    service_type_display = serializers.CharField(source='get_service_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Referral
        fields = [
            'id', 'patient_card', 'patient_name',
            'referring_doctor', 'referring_doctor_name',
            'target_doctor', 'target_doctor_name',
            'service_type', 'service_type_display', 'service_detail',
            'priority', 'priority_display',
            'scheduled_at', 'comment', 'status', 'status_display',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['status', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'referring_doctor': {'required': False, 'allow_null': True},
        }

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user

        if not validated_data.get('referring_doctor') and request.user.role in ('doctor', 'old'):
            validated_data['referring_doctor'] = request.user

        referral = super().create(validated_data)
        process_referral(referral, request.user)
        return referral


# ==================== MEDICATION ORDER ====================

class MedicationOrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True)
    prescribed_by_name = serializers.CharField(source='prescribed_by.full_name', read_only=True, default=None)
    medicine_type_display = serializers.CharField(source='get_medicine_type_display', read_only=True)
    food_relation_display = serializers.CharField(source='get_food_relation_display', read_only=True)
    generated_tasks_count = serializers.SerializerMethodField()

    class Meta:
        model = MedicationOrder
        fields = [
            'id', 'patient_card', 'patient_name',
            'prescribed_by', 'prescribed_by_name',
            'medicine_name', 'medicine_type', 'medicine_type_display',
            'duration_days', 'times_per_day', 'administration_times',
            'food_relation', 'food_relation_display',
            'single_dose', 'max_daily_dose', 'special_instructions', 'doctor_comment',
            'start_date', 'status', 'generated_tasks_count',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = ['status', 'created_by', 'created_at', 'updated_at']
        extra_kwargs = {
            'prescribed_by': {'required': False, 'allow_null': True},
        }

    def validate(self, attrs):
        times = attrs.get('administration_times')
        times_per_day = attrs.get('times_per_day')
        if self.instance is not None:
            times = times if times is not None else self.instance.administration_times
            times_per_day = times_per_day if times_per_day is not None else self.instance.times_per_day

        if times is not None:
            if not isinstance(times, list) or not times:
                raise serializers.ValidationError({'administration_times': "Kamida bitta vaqt kiritilishi kerak."})
            if times_per_day is not None and len(times) != times_per_day:
                raise serializers.ValidationError({
                    'administration_times': "Vaqtlar soni 'times_per_day' ga teng bo'lishi kerak."
                })
            for t in times:
                try:
                    hh, mm = str(t).split(':')
                    if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                        raise ValueError
                except (ValueError, AttributeError):
                    raise serializers.ValidationError({
                        'administration_times': f"Noto'g'ri vaqt formati: {t!r} (kutilgan: HH:MM)"
                    })
        return attrs

    def get_generated_tasks_count(self, obj):
        return obj.duration_days * obj.times_per_day

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user

        if not validated_data.get('prescribed_by') and request.user.role in ('doctor', 'old'):
            validated_data['prescribed_by'] = request.user

        order = super().create(validated_data)
        process_medication_order(order)
        return order


# ==================== NURSE TASK ====================

class TaskCompletionLogSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    delay_reason_display = serializers.CharField(source='get_delay_reason_display', read_only=True, default='')

    class Meta:
        model = TaskCompletionLog
        fields = [
            'id', 'task', 'performed_by', 'performed_by_name', 'performed_at',
            'action', 'action_display', 'comment', 'delay_reason', 'delay_reason_display',
        ]
        read_only_fields = fields

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.get_full_name() or obj.performed_by.username
        return None


class NurseTaskSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True)
    department_name = serializers.CharField(source='patient_card.department.name', read_only=True, default=None)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delay_reason_display = serializers.CharField(source='get_delay_reason_display', read_only=True, default='')
    completion_logs = TaskCompletionLogSerializer(many=True, read_only=True)

    class Meta:
        model = NurseTask
        fields = [
            'id', 'patient_card', 'patient_name', 'department_name',
            'task_type', 'task_type_display', 'title', 'scheduled_at',
            'status', 'status_display', 'notes',
            'delay_reason', 'delay_reason_display', 'delayed_at', 'is_overdue',
            'completion_logs', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class TaskActionSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')
    delay_reason = serializers.ChoiceField(
        choices=NurseTask.DELAY_REASON_CHOICES, required=False, allow_blank=True, default='',
    )


# ==================== EMERGENCY ====================

class EmergencyEventSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True, default=None)
    reported_by_name = serializers.SerializerMethodField()
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    notified_doctors_names = serializers.SerializerMethodField()
    notified_head_name = serializers.SerializerMethodField()

    class Meta:
        model = EmergencyEvent
        fields = [
            'id', 'patient_card', 'patient_name', 'department', 'department_name',
            'reported_by', 'reported_by_name', 'event_type', 'event_type_display',
            'description', 'status', 'status_display', 'occurred_at', 'resolved_at',
            'notified_doctors_names', 'notified_head_name',
        ]
        read_only_fields = [
            'department', 'reported_by', 'status', 'occurred_at', 'resolved_at',
            'notified_doctors_names', 'notified_head_name',
        ]

    def get_reported_by_name(self, obj):
        if obj.reported_by:
            return obj.reported_by.get_full_name() or obj.reported_by.username
        return None

    def get_notified_doctors_names(self, obj):
        return [u.get_full_name() or u.username for u in obj.notified_doctors.all()]

    def get_notified_head_name(self, obj):
        if obj.notified_head:
            return obj.notified_head.get_full_name() or obj.notified_head.username
        return None

    def create(self, validated_data):
        request = self.context['request']
        return report_emergency(
            patient_card=validated_data['patient_card'],
            reported_by=request.user,
            event_type=validated_data['event_type'],
            description=validated_data.get('description', ''),
        )


class EmergencyResolveSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default='')


# ==================== NOTIFICATION ====================

class NotificationSerializer(serializers.ModelSerializer):
    notification_type_display = serializers.CharField(source='get_notification_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True, default=None)

    class Meta:
        model = Notification
        fields = [
            'id', 'notification_type', 'notification_type_display', 'title', 'message',
            'priority', 'priority_display', 'patient_card', 'patient_name',
            'is_read', 'created_at',
        ]
        read_only_fields = fields


# ==================== AUDIT LOG ====================

class AuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    patient_name = serializers.CharField(source='patient_card.full_name', read_only=True, default=None)
    target_type = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'actor', 'actor_name', 'patient_card', 'patient_name',
            'target_type', 'object_id', 'action', 'action_display',
            'field_name', 'old_value', 'new_value', 'description', 'created_at',
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor:
            return obj.actor.get_full_name() or obj.actor.username
        return None

    def get_target_type(self, obj):
        return obj.content_type.model if obj.content_type else None


# ==================== PATIENT CARE OVERVIEW (mini serializers) ====================

class ConsultationMiniSerializer(serializers.ModelSerializer):
    specialty_display = serializers.CharField(source='get_specialty_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ConsultationRequest
        fields = ['id', 'specialty', 'specialty_display', 'reason', 'status', 'status_display', 'created_at']


class DiagnosticMiniSerializer(serializers.ModelSerializer):
    diagnostic_type_display = serializers.CharField(source='get_diagnostic_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = DiagnosticAssignment
        fields = ['id', 'diagnostic_type', 'diagnostic_type_display', 'notes', 'status', 'status_display', 'created_at']


class LabTestMiniSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LabTestAssignment
        fields = ['id', 'test_name', 'notes', 'status', 'status_display', 'created_at']


class MedicationOrderMiniSerializer(serializers.ModelSerializer):
    medicine_type_display = serializers.CharField(source='get_medicine_type_display', read_only=True)

    class Meta:
        model = MedicationOrder
        fields = [
            'id', 'medicine_name', 'medicine_type', 'medicine_type_display',
            'duration_days', 'times_per_day', 'administration_times',
            'start_date', 'status',
        ]
