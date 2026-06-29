# apps/care/services.py
"""
Referral / MedicationOrder / NurseTask / EmergencyEvent uchun biznes-logika.
Viewlar/serializerlar bu funksiyalarni chaqiradi — model.save() ichida side-effect yo'q.
"""

from datetime import datetime, timedelta, time as dt_time

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from apps.patients.models import (
    ConsultationRequest, DiagnosticAssignment, LabTestAssignment, TreatmentProcedure,
    Doctor,
)

from .models import (
    AuditLog, EmergencyEvent, MedicationOrder, NurseTask, Notification, Referral,
    TaskCompletionLog,
)
from .tasks import deliver_patient_telegram_notification


# ==================== REFERRAL ====================

def _referral_task_title(referral):
    type_label = referral.get_service_type_display()

    if referral.service_type == 'consultation':
        if referral.target_doctor_id:
            return f"{referral.target_doctor.full_name} konsultatsiyasi"
        specialty_label = dict(ConsultationRequest.SPECIALTY_CHOICES).get(referral.service_detail)
        return f"{specialty_label or type_label} konsultatsiyasi"

    if referral.service_type == 'diagnostic':
        diag_label = dict(DiagnosticAssignment.TYPE_CHOICES).get(referral.service_detail)
        return f"{diag_label or type_label} tekshiruvi"

    if referral.service_type == 'lab':
        return referral.service_detail or "Laboratoriya tekshiruvi"

    if referral.service_type == 'treatment':
        return referral.service_detail or "Muolaja"

    return referral.service_detail or type_label


def process_referral(referral, request_user):
    """Referral yaratilgandan keyin chaqiriladi: bog'liq yozuv, hamshira vazifasi,
    bildirishnomalar va audit log yaratadi."""
    patient = referral.patient_card
    linked_obj = None

    if referral.service_type == 'consultation':
        specialty = referral.service_detail
        valid_specialties = {c[0] for c in ConsultationRequest.SPECIALTY_CHOICES}
        if specialty not in valid_specialties:
            specialty = 'consilium'
        linked_obj = ConsultationRequest.objects.create(
            patient_card=patient,
            requested_by=referral.referring_doctor,
            specialty=specialty,
            reason=referral.comment,
        )
        if referral.target_doctor_id:
            linked_obj.consultants.add(referral.target_doctor)

    elif referral.service_type == 'diagnostic':
        diagnostic_type = referral.service_detail
        valid_types = {c[0] for c in DiagnosticAssignment.TYPE_CHOICES}
        if diagnostic_type not in valid_types:
            diagnostic_type = 'other'
        linked_obj = DiagnosticAssignment.objects.create(
            patient_card=patient,
            assigned_by=referral.referring_doctor,
            diagnostic_type=diagnostic_type,
            notes=referral.comment,
        )

    elif referral.service_type == 'lab':
        linked_obj = LabTestAssignment.objects.create(
            patient_card=patient,
            assigned_by=referral.referring_doctor,
            test_name=referral.service_detail or "Laboratoriya tekshiruvi",
            notes=referral.comment,
        )

    elif referral.service_type == 'treatment':
        linked_obj = TreatmentProcedure.objects.create(
            patient_card=patient,
            assigned_by=referral.referring_doctor,
            medicine_name=referral.service_detail or "Muolaja",
            schedule_note=referral.scheduled_at.strftime('%d.%m.%Y %H:%M'),
            notes=referral.comment,
        )

    if linked_obj is not None:
        referral.content_type = ContentType.objects.get_for_model(linked_obj)
        referral.object_id = linked_obj.pk
        referral.save(update_fields=['content_type', 'object_id'])

    task_type_map = {
        'consultation': 'consultation',
        'diagnostic':   'diagnostic',
        'lab':          'lab',
        'treatment':    'procedure',
        'other':        'other',
    }
    title = _referral_task_title(referral)
    referral_ct = ContentType.objects.get_for_model(referral)

    task = NurseTask.objects.create(
        patient_card=patient,
        task_type=task_type_map[referral.service_type],
        title=title,
        scheduled_at=referral.scheduled_at,
        notes=referral.comment,
        content_type=referral_ct,
        object_id=referral.pk,
    )

    priority = 'urgent' if referral.priority != 'normal' else 'normal'

    patient_notif = Notification.objects.create(
        patient_card=patient,
        notification_type='referral',
        title="Yangi yo'llanma",
        message=title,
        priority=priority,
        content_type=referral_ct,
        object_id=referral.pk,
    )
    try:
        deliver_patient_telegram_notification.delay(patient_notif.pk)
    except Exception:
        # Broker (Redis/Celery) mavjud bo'lmasa ham yo'llanma yaratilishi to'xtamasin
        pass

    if referral.target_doctor_id and referral.target_doctor.user_id:
        Notification.objects.create(
            recipient=referral.target_doctor.user,
            patient_card=patient,
            notification_type='referral',
            title="Yangi yo'llanma",
            message=title,
            priority=priority,
            content_type=referral_ct,
            object_id=referral.pk,
        )

    AuditLog.objects.create(
        actor=request_user,
        patient_card=patient,
        content_type=referral_ct,
        object_id=referral.pk,
        action='created',
        description=f"Yo'llanma yaratildi: {title}",
    )

    return task


# ==================== MEDICATION ORDER ====================

def process_medication_order(order):
    """MedicationOrder yaratilgandan keyin barcha qabul vaqtlari uchun
    NurseTask yozuvlarini generatsiya qiladi."""
    patient = order.patient_card
    is_injection = order.medicine_type == 'injection'
    task_type = 'injection' if is_injection else 'medication'
    title = f"{order.medicine_name} ukoli" if is_injection else f"{order.medicine_name} berish"

    notes_parts = []
    if order.single_dose:
        notes_parts.append(f"Doza: {order.single_dose}")
    if order.food_relation != 'none':
        food_label = dict(MedicationOrder.FOOD_RELATION_CHOICES).get(order.food_relation)
        if food_label:
            notes_parts.append(food_label)
    if order.special_instructions:
        notes_parts.append(order.special_instructions)
    notes = " | ".join(notes_parts)

    ct = ContentType.objects.get_for_model(order)
    tasks = []
    for day_offset in range(order.duration_days):
        date = order.start_date + timedelta(days=day_offset)
        for t_str in order.administration_times:
            hh, mm = (int(p) for p in t_str.split(':')[:2])
            naive_dt = datetime.combine(date, dt_time(hour=hh, minute=mm))
            scheduled_at = timezone.make_aware(naive_dt) if timezone.is_naive(naive_dt) else naive_dt
            tasks.append(NurseTask(
                patient_card=patient,
                task_type=task_type,
                title=title,
                scheduled_at=scheduled_at,
                notes=notes,
                content_type=ct,
                object_id=order.pk,
            ))

    NurseTask.objects.bulk_create(tasks)

    AuditLog.objects.create(
        actor=order.created_by,
        patient_card=patient,
        content_type=ct,
        object_id=order.pk,
        action='created',
        description=f"Dori tayinlandi: {order.medicine_name} ({len(tasks)} ta vazifa)",
    )

    return tasks


# ==================== NURSE TASK ====================

def complete_task(task, user, action, comment='', delay_reason=''):
    """NurseTask holatini o'zgartiradi, TaskCompletionLog va AuditLog yozadi."""
    old_status = task.status
    task.status = action

    if action == 'delayed':
        task.delayed_at = timezone.now()
        task.delay_reason = delay_reason
    elif action in ('cancelled', 'missed'):
        task.delay_reason = delay_reason

    task.save()

    TaskCompletionLog.objects.create(
        task=task,
        performed_by=user,
        action=action,
        comment=comment,
        delay_reason=delay_reason,
    )

    status_labels = dict(NurseTask.STATUS_CHOICES)
    AuditLog.objects.create(
        actor=user,
        patient_card=task.patient_card,
        content_type=ContentType.objects.get_for_model(task),
        object_id=task.pk,
        action='status_changed',
        field_name='status',
        old_value=old_status,
        new_value=action,
        description=f"Vazifa holati: {status_labels.get(old_status)} → {status_labels.get(action)}",
    )

    return task


# ==================== EMERGENCY ====================

def get_emergency_recipients(patient_card):
    """(navbatchi shifokorlar, bo'lim mudirlari) — CustomUser ro'yxatlari."""
    User = get_user_model()
    doctors = set()

    if patient_card.attending_doctor_id and patient_card.attending_doctor.user_id:
        doctors.add(patient_card.attending_doctor.user)

    if not doctors and patient_card.department_id:
        dept_doctors = User.objects.filter(role='doctor').filter(
            models.Q(department_id=patient_card.department_id)
            | models.Q(departments=patient_card.department_id)
        ).distinct()
        doctors.update(dept_doctors)

    heads = []
    if patient_card.department_id:
        head_doctors = Doctor.objects.filter(
            department_id=patient_card.department_id,
            is_head=True, is_active=True, user__isnull=False,
        ).select_related('user')
        heads = [d.user for d in head_doctors]

    return list(doctors), heads


def report_emergency(patient_card, reported_by, event_type, description):
    """EmergencyEvent yaratadi, navbatchi shifokor va bo'lim mudiriga bildirishnoma
    yuboradi, audit log yozadi."""
    event = EmergencyEvent.objects.create(
        patient_card=patient_card,
        department=patient_card.department,
        reported_by=reported_by,
        event_type=event_type,
        description=description,
    )

    doctors, heads = get_emergency_recipients(patient_card)
    title = "Favqulodda holat!"
    message = f"{patient_card.full_name}: {event.get_event_type_display()}"
    ct = ContentType.objects.get_for_model(event)

    for doc_user in doctors:
        Notification.objects.create(
            recipient=doc_user, patient_card=patient_card,
            notification_type='emergency', title=title, message=message,
            priority='urgent', content_type=ct, object_id=event.pk,
        )
    if doctors:
        event.notified_doctors.set(doctors)

    for head_user in heads:
        Notification.objects.create(
            recipient=head_user, patient_card=patient_card,
            notification_type='emergency', title=title, message=message,
            priority='urgent', content_type=ct, object_id=event.pk,
        )
    if heads:
        event.notified_head = heads[0]
        event.save(update_fields=['notified_head'])

    AuditLog.objects.create(
        actor=reported_by,
        patient_card=patient_card,
        content_type=ct,
        object_id=event.pk,
        action='created',
        description=f"Favqulodda holat: {event.get_event_type_display()}",
    )

    return event


def resolve_emergency(event, user, comment=''):
    event.status = 'resolved'
    event.resolved_at = timezone.now()
    event.save(update_fields=['status', 'resolved_at'])

    AuditLog.objects.create(
        actor=user,
        patient_card=event.patient_card,
        content_type=ContentType.objects.get_for_model(event),
        object_id=event.pk,
        action='resolved',
        description=comment or "Favqulodda holat hal qilindi",
    )

    return event
