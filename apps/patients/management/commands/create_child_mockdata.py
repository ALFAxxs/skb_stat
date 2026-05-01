# apps/patients/management/commands/create_child_mockdata.py
"""
16 yoshga to'lmagan temir yo'lchi bemorlar uchun mockdata yaratish.

Ishlatish:
    python manage.py create_child_mockdata
    python manage.py create_child_mockdata --count 10
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random
from datetime import date, timedelta


CHILDREN = [
    ("Rahimov Alibek Jasurovich",       "M", "2018-03-15", "14256789012345"),
    ("Karimova Nilufar Bekovna",         "F", "2019-07-22", "28156789012346"),
    ("Toshmatov Sardor Alievich",        "M", "2020-01-10", "14356789012347"),
    ("Yusupova Zulfiya Hamidovna",       "F", "2017-11-05", "28456789012348"),
    ("Mirzayev Doniyor Ulugbekovich",    "M", "2021-04-18", "14556789012349"),
    ("Hasanova Malika Ismoilovna",       "F", "2016-08-30", "28656789012350"),
    ("Qodirov Umid Baxtiyorovich",       "M", "2022-02-14", "14756789012351"),
    ("Nazarova Shahnoza Rustamovna",     "F", "2015-12-25", "28856789012352"),
    ("Ergashev Sherzod Mansurovich",     "M", "2023-06-08", "14956789012353"),
    ("Abdullayeva Dilnoza Hamzaevna",    "F", "2014-09-17", "29056789012354"),
]

PARENTS = [
    ("Rahimov Jasur Bekovich",     "14200000000001"),
    ("Karimov Bekzod Alimovich",   "14200000000002"),
    ("Toshmatov Ali Hamidovich",   "14200000000003"),
    ("Yusupov Hamid Ergashevich",  "14200000000004"),
    ("Mirzayev Ulugbek Sobirovich","14200000000005"),
    ("Hasanov Ismoil Tursunovich", "14200000000006"),
    ("Qodirov Baxtiyar Norovich",  "14200000000007"),
    ("Nazarov Rustam Karimovich",  "14200000000008"),
    ("Ergashev Mansur Yusupovich", "14200000000009"),
    ("Abdullayev Hamza Alievich",  "14200000000010"),
]

DIAGNOSES = [
    "O'tkir bronxit",
    "Pnevmoniya",
    "Angina",
    "ORVI",
    "Gastrit",
    "Appenditsit",
    "Sinusit",
    "Otit",
    "Allergik rinit",
    "Tonsillitl",
]


class Command(BaseCommand):
    help = "16 yoshga to'lmagan temir yo'lchi bemorlar uchun mockdata"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=5,
            help="Nechta bemor yaratish (max 10, default 5)")

    def handle(self, *args, **options):
        from apps.patients.models import (
            PatientCard, Organization, Department, Doctor
        )
        from apps.services.models import (
            Service, PatientService, Medicine, PatientMedicine
        )
        from apps.users.models import CustomUser

        count = min(options['count'], 10)

        # Bazaviy ob'ektlarni olish
        orgs = list(Organization.objects.all()[:20])
        depts = list(Department.objects.filter(is_active=True)[:5])
        doctors = list(Doctor.objects.filter(is_active=True)[:10])
        services = list(Service.objects.filter(is_active=True)[:30])
        medicines = list(Medicine.objects.filter(is_active=True)[:20])
        admin_user = CustomUser.objects.filter(is_superuser=True).first() or \
                     CustomUser.objects.first()

        if not orgs:
            self.stderr.write("Tashkilotlar topilmadi. import_organizations ni ishga tushiring.")
            return
        if not services:
            self.stderr.write("Xizmatlar topilmadi.")
            return

        created = 0
        for i in range(count):
            name, gender, bdate_str, jshshir = CHILDREN[i]
            parent_name, parent_jshshir = PARENTS[i]
            birth_date = date.fromisoformat(bdate_str)
            org = random.choice(orgs)
            dept = random.choice(depts) if depts else None
            doctor = random.choice(doctors) if doctors else None

            # Qabul sanasi — oxirgi 6 oy ichida
            days_ago = random.randint(1, 180)
            admission_dt = timezone.now() - timedelta(days=days_ago)

            # Bayonnoma raqami
            import uuid
            record_num = f"{admission_dt.year}-{str(uuid.uuid4())[:6].upper()}"
            while PatientCard.objects.filter(medical_record_number=record_num).exists():
                record_num = f"{admission_dt.year}-{str(uuid.uuid4())[:6].upper()}"

            patient = PatientCard.objects.create(
                medical_record_number=record_num,
                full_name=name,
                gender=gender,
                birth_date=birth_date,
                JSHSHIR=jshshir,
                patient_category='railway',
                social_status='dependent',
                visit_type='inpatient',
                status='completed',
                admission_date=admission_dt,
                discharge_date=admission_dt + timedelta(days=random.randint(3, 14)),
                department=dept,
                attending_doctor=doctor,
                workplace_org=org,
                admission_diagnosis=random.choice(DIAGNOSES),
                parent_name=parent_name,
                parent_jshshir=parent_jshshir,
                parent_workplace_org=org,
                registered_by=admin_user,
                region=None,
            )

            # Xizmatlar qo'shish (2-5 ta)
            svc_count = random.randint(2, 5)
            for svc in random.sample(services, min(svc_count, len(services))):
                price = svc.price_for_patient('railway')
                qty = random.randint(1, 3)
                PatientService.objects.create(
                    patient_card=patient,
                    service=svc,
                    quantity=qty,
                    price=price,
                    patient_category_at_order='railway',
                    ordered_by=doctor,
                    status='completed',
                )

            # Dorilar qo'shish (1-4 ta)
            if medicines:
                med_count = random.randint(1, 4)
                for med in random.sample(medicines, min(med_count, len(medicines))):
                    qty = Decimal(str(random.randint(1, 10)))
                    price = Decimal(str(random.randint(5000, 150000)))
                    PatientMedicine.objects.create(
                        patient_card=patient,
                        medicine=med,
                        quantity=qty,
                        price=price,
                        ordered_by=doctor,
                    )

            svc_total = sum(
                float(ps.total_price)
                for ps in PatientService.objects.filter(patient_card=patient)
            )
            med_total = sum(
                float(pm.total_price)
                for pm in PatientMedicine.objects.filter(patient_card=patient)
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ {name} ({birth_date}) | "
                    f"Ota-ona: {parent_name} | "
                    f"Org: {org} | "
                    f"Xizmat: {svc_total:,.0f} so'm | "
                    f"Dori: {med_total:,.0f} so'm"
                )
            )
            created += 1

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Jami {created} ta bola bemor yaratildi"
        ))