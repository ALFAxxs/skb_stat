# apps/care/views.py

from datetime import datetime

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.patients.models import (
    ConsultationRequest, DiagnosticAssignment, Doctor, LabTestAssignment, PatientCard,
)

from .filters import AuditLogFilter, EmergencyEventFilter, NurseTaskFilter, ReferralFilter
from .models import AuditLog, EmergencyEvent, MedicationOrder, NurseTask, Notification, Referral
from .permissions import (
    IsDeptHeadOrAdmin, IsDoctorOrAdmin, IsNurseOrAdmin, scope_to_user_departments,
)
from .serializers import (
    AuditLogSerializer, ConsultationMiniSerializer, DiagnosticMiniSerializer, DoctorSerializer,
    EmergencyEventSerializer, EmergencyResolveSerializer, LabTestMiniSerializer,
    MedicationOrderMiniSerializer, MedicationOrderSerializer, NotificationSerializer,
    NurseTaskSerializer, ReferralSerializer, TaskActionSerializer,
)
from .services import complete_task, resolve_emergency


# ==================== REFERRAL ====================

class ReferralViewSet(viewsets.ModelViewSet):
    """Yo'llanmalar — yaratish (shifokor/admin), ro'yxat/ko'rish (bo'lim bo'yicha cheklangan)."""
    queryset = Referral.objects.select_related(
        'patient_card', 'referring_doctor', 'target_doctor', 'created_by',
    )
    serializer_class = ReferralSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ReferralFilter
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsDoctorOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return scope_to_user_departments(super().get_queryset(), self.request.user)


# ==================== MEDICATION ORDER ====================

class MedicationOrderViewSet(viewsets.ModelViewSet):
    """Dori/muolaja tayinlash — yaratish (shifokor/admin), ro'yxat/ko'rish (bo'lim bo'yicha cheklangan)."""
    queryset = MedicationOrder.objects.select_related('patient_card', 'prescribed_by', 'created_by')
    serializer_class = MedicationOrderSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'medicine_type', 'patient_card']
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsDoctorOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return scope_to_user_departments(super().get_queryset(), self.request.user)


# ==================== NURSE TASK ====================

class NurseTaskViewSet(viewsets.ReadOnlyModelViewSet):
    """Hamshira kunlik vazifalari + bajarish/kechiktirish/bekor qilish/o'tkazib yuborish amallari."""
    queryset = NurseTask.objects.select_related(
        'patient_card', 'patient_card__department',
    ).prefetch_related('completion_logs')
    serializer_class = NurseTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = NurseTaskFilter

    def get_queryset(self):
        return scope_to_user_departments(super().get_queryset(), self.request.user)

    def _apply_action(self, request, action_name, require_delay_reason=False):
        task = self.get_object()
        serializer = TaskActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if require_delay_reason and not data.get('delay_reason'):
            return Response(
                {'delay_reason': _("Bu maydon majburiy.")}, status=status.HTTP_400_BAD_REQUEST,
            )

        task = complete_task(
            task, request.user, action_name,
            comment=data.get('comment', ''), delay_reason=data.get('delay_reason', ''),
        )
        return Response(NurseTaskSerializer(task, context={'request': request}).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsNurseOrAdmin])
    def complete(self, request, pk=None):
        return self._apply_action(request, 'done')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsNurseOrAdmin])
    def delay(self, request, pk=None):
        return self._apply_action(request, 'delayed', require_delay_reason=True)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsNurseOrAdmin])
    def cancel(self, request, pk=None):
        return self._apply_action(request, 'cancelled', require_delay_reason=True)

    @action(detail=True, methods=['post'], url_path='miss', permission_classes=[IsAuthenticated, IsNurseOrAdmin])
    def mark_missed(self, request, pk=None):
        return self._apply_action(request, 'missed', require_delay_reason=True)


# ==================== EMERGENCY EVENT ====================

class EmergencyEventViewSet(viewsets.ModelViewSet):
    """Favqulodda holatlar — yaratish (hamshira/admin), hal qilish (bo'lim mudiri/admin)."""
    queryset = EmergencyEvent.objects.select_related(
        'patient_card', 'department', 'reported_by', 'notified_head',
    ).prefetch_related('notified_doctors')
    serializer_class = EmergencyEventSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = EmergencyEventFilter
    http_method_names = ['get', 'post', 'head', 'options']

    def get_permissions(self):
        if self.action == 'create':
            return [IsAuthenticated(), IsNurseOrAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        return scope_to_user_departments(super().get_queryset(), self.request.user, path='patient_card__department_id')

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsDeptHeadOrAdmin])
    def resolve(self, request, pk=None):
        event = self.get_object()
        serializer = EmergencyResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        event = resolve_emergency(event, request.user, comment=serializer.validated_data.get('comment', ''))
        return Response(EmergencyEventSerializer(event, context={'request': request}).data)


# ==================== NOTIFICATION ====================

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Joriy foydalanuvchining bildirishnomalari (polling)."""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(recipient=self.request.user).select_related('patient_card')
        unread = self.request.query_params.get('unread')
        if unread is not None and unread.lower() in ('1', 'true', 'yes'):
            qs = qs.filter(is_read=False)
        return qs

    @action(detail=True, methods=['post'], url_path='mark-read')
    def mark_read(self, request, pk=None):
        notif = self.get_object()
        notif.mark_read()
        return Response(NotificationSerializer(notif, context={'request': request}).data)


# ==================== AUDIT LOG ====================

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Audit jurnal — faqat bo'lim mudiri/admin ko'ra oladi."""
    queryset = AuditLog.objects.select_related('actor', 'patient_card', 'content_type')
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, IsDeptHeadOrAdmin]
    filter_backends = [DjangoFilterBackend]
    filterset_class = AuditLogFilter

    def get_queryset(self):
        return scope_to_user_departments(super().get_queryset(), self.request.user)


# ==================== DASHBOARD ====================

class DashboardView(APIView):
    """GET /api/care/dashboard/?date=YYYY-MM-DD&department=<id> — monitoring ko'rsatkichlari."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        date_str = request.query_params.get('date')
        if date_str:
            try:
                target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': _("Sana formati: YYYY-MM-DD")}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_date = timezone.localdate()

        qs = NurseTask.objects.filter(scheduled_at__date=target_date)
        qs = scope_to_user_departments(qs, request.user)

        department = request.query_params.get('department')
        if department:
            qs = qs.filter(patient_card__department_id=department)

        now = timezone.now()
        due_now_qs = qs.filter(status='pending', scheduled_at__lte=now).select_related('patient_card')

        emergency_qs = EmergencyEvent.objects.filter(occurred_at__date=target_date)
        emergency_qs = scope_to_user_departments(emergency_qs, request.user, path='patient_card__department_id')
        if department:
            emergency_qs = emergency_qs.filter(department_id=department)

        return Response({
            'date': target_date.isoformat(),
            'total': qs.count(),
            'pending': qs.filter(status='pending').count(),
            'done': qs.filter(status='done').count(),
            'delayed': qs.filter(status='delayed').count(),
            'missed': qs.filter(status='missed').count(),
            'cancelled': qs.filter(status='cancelled').count(),
            'due_now': NurseTaskSerializer(due_now_qs, many=True, context={'request': request}).data,
            'emergency_count_today': emergency_qs.count(),
        })


# ==================== PATIENT CARE OVERVIEW ====================

class PatientCareOverviewView(APIView):
    """GET /api/care/patients/<id>/overview/ — bemorning konsultatsiya/diagnostika/lab/dori jadvali."""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        patient = get_object_or_404(PatientCard, pk=pk)

        consultations = ConsultationRequest.objects.filter(patient_card=patient).order_by('-created_at')[:20]
        diagnostics = DiagnosticAssignment.objects.filter(patient_card=patient).order_by('-created_at')[:20]
        lab_tests = LabTestAssignment.objects.filter(patient_card=patient).order_by('-created_at')[:20]
        medications = MedicationOrder.objects.filter(
            patient_card=patient, status='active',
        ).select_related('prescribed_by')
        upcoming_tasks = NurseTask.objects.filter(
            patient_card=patient, status='pending', task_type__in=['medication', 'injection'],
        ).order_by('scheduled_at')[:50]

        return Response({
            'patient': {
                'id': patient.pk,
                'full_name': patient.full_name,
                'department': patient.department.name if patient.department_id else None,
            },
            'consultations': ConsultationMiniSerializer(consultations, many=True).data,
            'diagnostics': DiagnosticMiniSerializer(diagnostics, many=True).data,
            'lab_tests': LabTestMiniSerializer(lab_tests, many=True).data,
            'medications': MedicationOrderMiniSerializer(medications, many=True).data,
            'upcoming_tasks': NurseTaskSerializer(upcoming_tasks, many=True, context={'request': request}).data,
        })


# ==================== DOCTOR LIST ====================

class DoctorListView(generics.ListAPIView):
    """GET /api/care/doctors/ — yo'llanma uchun shifokorlar ro'yxati."""
    queryset = Doctor.objects.filter(is_active=True).select_related('department').order_by('full_name')
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['department']
