# apps/care/tests.py

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.patients.models import ConsultationRequest, Department, PatientCard

from .models import AuditLog, EmergencyEvent, MedicationOrder, NurseTask, Notification, Referral
from .tasks import check_overdue_tasks

User = get_user_model()


class CareApiTests(TestCase):
    def setUp(self):
        self.department = Department.objects.create(name="Kardiologiya")

        self.doctor_user = User.objects.create_user(
            username='doctor1', password='pass12345', role='doctor', department=self.department,
        )
        self.nurse_user = User.objects.create_user(
            username='nurse1', password='pass12345', role='nurse', department=self.department,
        )
        self.head_user = User.objects.create_user(
            username='head1', password='pass12345', role='doctor', department=self.department,
            is_head=True,
        )

        self.patient = PatientCard.objects.create(
            medical_record_number="MR-001",
            full_name="Test Bemor",
            gender='M',
            birth_date='1980-01-01',
            admission_date=timezone.now(),
            department=self.department,
            attending_doctor=self.doctor_user,
        )

        self.doctor_client = APIClient()
        self.doctor_client.force_authenticate(user=self.doctor_user)

        self.nurse_client = APIClient()
        self.nurse_client.force_authenticate(user=self.nurse_user)

        self.head_client = APIClient()
        self.head_client.force_authenticate(user=self.head_user)

    # ---------------------------------------------------------------
    def test_token_auth(self):
        client = APIClient()
        resp = client.post(reverse('api-auth-token'), {'username': 'doctor1', 'password': 'pass12345'})
        self.assertEqual(resp.status_code, 200)
        token = resp.data['token']

        client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
        resp = client.get('/api/care/doctors/')
        self.assertEqual(resp.status_code, 200)

    # ---------------------------------------------------------------
    def test_referral_creates_consultation_and_task(self):
        scheduled_at = timezone.now() + timedelta(hours=2)
        payload = {
            'patient_card': self.patient.pk,
            'service_type': 'consultation',
            'service_detail': 'cardiology',
            'priority': 'urgent',
            'scheduled_at': scheduled_at.isoformat(),
            'comment': 'Konsultatsiya kerak',
        }
        resp = self.doctor_client.post('/api/care/referrals/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        referral = Referral.objects.get(pk=resp.data['id'])
        self.assertEqual(referral.created_by, self.doctor_user)
        self.assertEqual(referral.referring_doctor, self.doctor_user)

        self.assertTrue(ConsultationRequest.objects.filter(patient_card=self.patient, specialty='cardiology').exists())

        task = NurseTask.objects.get(content_type__model='referral', object_id=referral.pk)
        self.assertEqual(task.task_type, 'consultation')
        self.assertEqual(task.status, 'pending')

        self.assertTrue(Notification.objects.filter(patient_card=self.patient, notification_type='referral').exists())
        self.assertTrue(AuditLog.objects.filter(patient_card=self.patient, action='created').exists())

        # Nurse can't create referrals
        resp = self.nurse_client.post('/api/care/referrals/', payload, format='json')
        self.assertEqual(resp.status_code, 403)

    # ---------------------------------------------------------------
    def test_medication_order_generates_tasks(self):
        payload = {
            'patient_card': self.patient.pk,
            'medicine_name': 'Aspirin',
            'medicine_type': 'tablet',
            'duration_days': 3,
            'times_per_day': 2,
            'administration_times': ['08:00', '20:00'],
            'food_relation': 'after_meal',
            'single_dose': '1 tabletka',
        }
        resp = self.doctor_client.post('/api/care/medication-orders/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        order = MedicationOrder.objects.get(pk=resp.data['id'])
        tasks = NurseTask.objects.filter(content_type__model='medicationorder', object_id=order.pk)
        self.assertEqual(tasks.count(), 6)
        self.assertTrue(all(t.task_type == 'medication' for t in tasks))

    # ---------------------------------------------------------------
    def test_task_complete_and_delay_flow(self):
        task = NurseTask.objects.create(
            patient_card=self.patient, task_type='medication', title='Dori berish',
            scheduled_at=timezone.now() - timedelta(minutes=10),
        )

        resp = self.doctor_client.post(f'/api/care/tasks/{task.pk}/complete/', {}, format='json')
        self.assertEqual(resp.status_code, 403)

        resp = self.nurse_client.post(f'/api/care/tasks/{task.pk}/complete/', {'comment': 'Dori berildi'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        task.refresh_from_db()
        self.assertEqual(task.status, 'done')
        self.assertTrue(task.completion_logs.filter(action='done').exists())
        self.assertTrue(AuditLog.objects.filter(object_id=task.pk, action='status_changed').exists())

        # delay requires a reason
        task2 = NurseTask.objects.create(
            patient_card=self.patient, task_type='injection', title='Ukol',
            scheduled_at=timezone.now() + timedelta(hours=1),
        )
        resp = self.nurse_client.post(f'/api/care/tasks/{task2.pk}/delay/', {}, format='json')
        self.assertEqual(resp.status_code, 400)

        resp = self.nurse_client.post(
            f'/api/care/tasks/{task2.pk}/delay/',
            {'delay_reason': 'patient_absent', 'comment': 'Bemor yo\'q edi'}, format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        task2.refresh_from_db()
        self.assertEqual(task2.status, 'delayed')
        self.assertEqual(task2.delay_reason, 'patient_absent')

    # ---------------------------------------------------------------
    def test_emergency_event_notifies_doctor_and_head(self):
        payload = {
            'patient_card': self.patient.pk,
            'event_type': 'condition_worsened',
            'description': 'Ahvoli yomonlashdi',
        }
        resp = self.nurse_client.post('/api/care/emergencies/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)

        event = EmergencyEvent.objects.get(pk=resp.data['id'])
        self.assertEqual(event.status, 'open')
        self.assertIn(self.doctor_user, event.notified_doctors.all())
        self.assertEqual(event.notified_head, self.head_user)

        self.assertTrue(Notification.objects.filter(
            recipient=self.doctor_user, notification_type='emergency', priority='urgent',
        ).exists())
        self.assertTrue(Notification.objects.filter(
            recipient=self.head_user, notification_type='emergency', priority='urgent',
        ).exists())

        # only dept head/admin can resolve
        resp = self.nurse_client.post(f'/api/care/emergencies/{event.pk}/resolve/', {}, format='json')
        self.assertEqual(resp.status_code, 403)

        resp = self.head_client.post(f'/api/care/emergencies/{event.pk}/resolve/', {'comment': 'Hal qilindi'}, format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        event.refresh_from_db()
        self.assertEqual(event.status, 'resolved')
        self.assertIsNotNone(event.resolved_at)

    # ---------------------------------------------------------------
    def test_dashboard_counts(self):
        now = timezone.now()
        NurseTask.objects.create(
            patient_card=self.patient, task_type='medication', title='Done task',
            scheduled_at=now, status='done',
        )
        NurseTask.objects.create(
            patient_card=self.patient, task_type='medication', title='Due now',
            scheduled_at=now - timedelta(minutes=5), status='pending',
        )

        resp = self.nurse_client.get('/api/care/dashboard/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['total'], 2)
        self.assertEqual(resp.data['done'], 1)
        self.assertEqual(resp.data['pending'], 1)
        self.assertEqual(len(resp.data['due_now']), 1)

    # ---------------------------------------------------------------
    def test_check_overdue_tasks_marks_delayed_and_missed(self):
        overdue = NurseTask.objects.create(
            patient_card=self.patient, task_type='medication', title='Overdue',
            scheduled_at=timezone.now() - timedelta(minutes=5), status='pending',
        )
        long_overdue = NurseTask.objects.create(
            patient_card=self.patient, task_type='medication', title='Long overdue',
            scheduled_at=timezone.now() - timedelta(hours=3), status='delayed', delayed_at=timezone.now() - timedelta(hours=3),
        )

        result = check_overdue_tasks()

        overdue.refresh_from_db()
        long_overdue.refresh_from_db()
        self.assertEqual(overdue.status, 'delayed')
        self.assertEqual(long_overdue.status, 'missed')
        self.assertEqual(result, {'delayed': 1, 'missed': 1})

        self.assertTrue(Notification.objects.filter(recipient=self.nurse_user, notification_type='task_delayed').exists())

    # ---------------------------------------------------------------
    def test_patient_overview(self):
        resp = self.doctor_client.get(f'/api/care/patients/{self.patient.pk}/overview/')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data['patient']['full_name'], 'Test Bemor')
        self.assertIn('consultations', resp.data)
        self.assertIn('medications', resp.data)
        self.assertIn('upcoming_tasks', resp.data)
