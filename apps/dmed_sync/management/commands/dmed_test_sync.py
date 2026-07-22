"""
Bitta bemor uchun DMED sync ni sinab ko'rish.

Ishlatish:
    python manage.py dmed_test_sync <patient_id>
    python manage.py dmed_test_sync <patient_id> --step patient
    python manage.py dmed_test_sync <patient_id> --step visit
"""
import asyncio
import traceback

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Bitta bemor uchun DMED sync ni sinab ko\'radi (headless=False)'

    def add_arguments(self, parser):
        parser.add_argument('patient_id', type=int, help='PatientCard PK')
        parser.add_argument(
            '--step',
            choices=['patient', 'visit', 'both'],
            default='both',
            help='Qaysi qadamni test qilish (default: both)',
        )

    def handle(self, *args, **options):
        from apps.patients.models import PatientCard

        pid = options['patient_id']
        step = options['step']

        try:
            patient = PatientCard.objects.select_related('attending_doctor').get(pk=pid)
        except PatientCard.DoesNotExist:
            raise CommandError(f'PatientCard #{pid} topilmadi')

        self.stdout.write(self.style.NOTICE(
            f'\n=== DMED Sync Test ===\n'
            f'Bemor    : {patient.full_name}\n'
            f'JSHSHIR  : {patient.JSHSHIR or "(yo'q)"}\n'
            f'Tur      : {patient.visit_type}\n'
            f'Shifokor : {patient.attending_doctor}\n'
            f'Qadam    : {step}\n'
        ))

        asyncio.run(self._run(patient, step))

    async def _run(self, patient, step):
        import django
        django.setup()

        from django.conf import settings
        # Test uchun majburiy ravishda headless=False
        original_headless = getattr(settings, 'DMED_HEADLESS', True)
        settings.DMED_HEADLESS = False

        try:
            from apps.dmed_sync.browser import dmed_session
            from apps.dmed_sync.tasks.patient import sync_patient
            from apps.dmed_sync.tasks.visit import sync_visit
            from apps.dmed_sync.models import DMEDSyncRecord

            role = 'Menejer'

            if step in ('patient', 'both'):
                self.stdout.write('\n▶ sync_patient boshlandi...')
                try:
                    async with dmed_session(role=role) as page:
                        dmed_id = await sync_patient(page, patient)
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ sync_patient muvaffaqiyatli. DMED tibbiy karta: {dmed_id}'
                    ))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(
                        f'❌ sync_patient xato: {exc}\n{traceback.format_exc()}'
                    ))
                    return

            if step in ('visit', 'both'):
                self.stdout.write('\n▶ sync_visit boshlandi...')
                try:
                    async with dmed_session(role=role) as page:
                        dmed_id = await sync_visit(page, patient)
                    self.stdout.write(self.style.SUCCESS(
                        f'✅ sync_visit muvaffaqiyatli. DMED qabul ID: {dmed_id or "(URL dan olinmadi)"}'
                    ))
                except Exception as exc:
                    self.stdout.write(self.style.ERROR(
                        f'❌ sync_visit xato: {exc}\n{traceback.format_exc()}'
                    ))

        finally:
            settings.DMED_HEADLESS = original_headless
