# apps/patients/management/commands/generate_mock_data.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime, timedelta
import random
import uuid
from apps.patients.models import (
    PatientCard, Organization, Department, Doctor,
    Country, Region, District, City, DeathCause, SurgicalOperation
)


class Command(BaseCommand):
    help = "Test uchun mock data yaratish"

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=50, help='Nechta bemor yaratish')
        parser.add_argument('--clear', action='store_true', help='Avval eski datani o\'chirish')

    def handle(self, *args, **options):
        count = options['count']

        if options['clear']:
            PatientCard.objects.all().delete()
            self.stdout.write("Eski ma'lumotlar o'chirildi.")

        # ==================== LOOKUP DATA ====================

        orgs = [
            "1-son shahar poliklinikasi",
            "2-son shahar poliklinikasi",
            "3-son shahar poliklinikasi",
            "Markaziy tuman shifoxonasi",
            "Oilaviy poliklinika №5",
            "Tez tibbiy yordam markazi",
            "Xususiy klinika MedPlus",
            "Sanitariya-epidemiologiya markazi",
        ]
        org_objects = []
        for name in orgs:
            obj, _ = Organization.objects.get_or_create(name=name)
            org_objects.append(obj)

        departments = [
            "Terapiya", "Jarrohlik", "Kardiologiya",
            "Nevrologiya", "Ortopediya", "Ginekologiya",
            "Pediatriya", "Reanimatsiya", "Travmatologiya",
            "Urologiya", "Endokrinologiya", "Pulmonologiya",
        ]
        dept_objects = []
        for name in departments:
            obj, _ = Department.objects.get_or_create(name=name)
            dept_objects.append(obj)

        doctors_data = [
            ("Karimov Bobur", False),
            ("Rahimova Nilufar", False),
            ("Toshmatov Jasur", False),
            ("Yusupova Malika", False),
            ("Hasanov Sherzod", False),
            ("Nazarova Dilorom", True),
            ("Qodirov Ulugbek", True),
            ("Mirzayev Akbar", True),
        ]
        doctor_objects = []
        head_doctors = []
        for full_name, is_head in doctors_data:
            obj, _ = Doctor.objects.get_or_create(
                full_name=full_name,
                defaults={
                    'department': random.choice(dept_objects),
                    'is_head': is_head
                }
            )
            doctor_objects.append(obj)
            if is_head:
                head_doctors.append(obj)

        country, _ = Country.objects.get_or_create(name="O'zbekiston")
        region, _ = Region.objects.get_or_create(name="Toshkent shahri", country=country)

        districts_list = [
            "Chilonzor", "Yunusobod", "Mirzo Ulug'bek",
            "Shayxontohur", "Yakkasaroy", "Uchtepa"
        ]
        district_objects = []
        for name in districts_list:
            obj, _ = District.objects.get_or_create(name=name, region=region)
            district_objects.append(obj)

        city_objects = []
        for district in district_objects:
            obj, _ = City.objects.get_or_create(
                name=f"{district.name} shahri",
                district=district
            )
            city_objects.append(obj)

        # ==================== MA'LUMOTLAR ====================

        erkak_ismlar = [
            "Karimov Bobur", "Rahimov Jasur", "Toshmatov Ulugbek",
            "Hasanov Sherzod", "Yusupov Akbar", "Nazarov Dilshod",
            "Qodirov Mansur", "Mirzayev Sardor", "Aliyev Firdavs",
            "Ergashev Nodir", "Sobirov Eldor", "Xoliqov Anvar",
            "Abdullayev Sanjar", "Normatov Zafar", "Usmonov Ibrohim",
            "Tursunov Hamid", "Baxtiyorov Otabek", "Xasanov Lochinbek",
            "Ismoilov Laziz", "Raximov Murod", "Jurayev Timur",
            "Holmatov Bekzod", "Sultonov Jahongir", "Nishonov Ravshan",
        ]
        ayol_ismlar = [
            "Karimova Nilufar", "Rahimova Malika", "Toshmatova Dilorom",
            "Hasanova Gulnora", "Yusupova Feruza", "Nazarova Shahnoza",
            "Qodirova Zulfiya", "Mirzayeva Mohira", "Aliyeva Maftuna",
            "Ergasheva Nasiba", "Sobirova Kamola", "Xoliqova Nargiza",
            "Abdullayeva Barno", "Normatova Hulkar", "Usmonova Sabohat",
            "Tursunova Gavhar", "Baxtiyorova Munira", "Xasanova Oydin",
            "Ismoilova Sarvinoz", "Raximova Lobar", "Jurayeva Dilnoza",
            "Holmatova Sevinch", "Sultonova Iroda", "Nishonova Zulfiya",
        ]

        mkb10_codes = [
            ("I21.0", "O'tkir transmural oldingi miokard infarkti"),
            ("I10",   "Gipertoniya kasalligi"),
            ("J18.9", "Aniqlanmagan pnevmoniya"),
            ("K35.8", "O'tkir appenditsit"),
            ("S72.0", "Son suyagi bo'yni sinishi"),
            ("I63.9", "Miya qon aylanishining o'tkir buzilishi"),
            ("K80.1", "O't pufagi toshi xoletsistit bilan"),
            ("N20.0", "Buyrak toshi"),
            ("J44.1", "OOKT o'tkir ziddiyat bilan"),
            ("E11.9", "2-tur qandli diabet"),
            ("C34.1", "Bronx va o'pka saratoni"),
            ("I50.0", "Yurak yetishmovchiligi"),
            ("K29.7", "Oshqozon yarasi"),
            ("M16.1", "Son-chanoq bo'g'imi artrozi"),
            ("G35",   "Ko'p skleroz"),
        ]

        kochalar = [
            "Amir Temur ko'chasi",
            "Mustaqillik shoh ko'chasi",
            "Navoiy ko'chasi",
            "Buyuk Ipak Yo'li ko'chasi",
            "Qoratosh ko'chasi",
            "Olmazor ko'chasi",
            "Bog'ishamol ko'chasi",
            "Chilonzor ko'chasi",
        ]

        operations_list = [
            "Appendektomiya",
            "Xoletsistektomiya",
            "O'pka rezektsiyasi",
            "Koronar shuntlash",
            "Artroplastika",
            "Nefrektomiya",
            "Gastroektomiya",
            "Grija plastikasi",
        ]

        # ==================== BEMORLAR YARATISH ====================

        created = 0
        skipped = 0

        for i in range(count):
            # Unique medical_record_number
            while True:
                year = random.randint(2023, 2025)
                record_number = f"{year}-{str(uuid.uuid4())[:6].upper()}"
                if not PatientCard.objects.filter(medical_record_number=record_number).exists():
                    break

            gender = random.choice(['M', 'F'])
            full_name = random.choice(erkak_ismlar if gender == 'M' else ayol_ismlar)

            birth_date = datetime(
                random.randint(1940, 2005),
                random.randint(1, 12),
                random.randint(1, 28)
            ).date()

            admission_date = timezone.now() - timedelta(days=random.randint(1, 730))
            days = random.randint(1, 30)
            discharge_date = admission_date + timedelta(days=days)

            outcome = random.choices(
                ['discharged', 'deceased', 'transferred'],
                weights=[80, 10, 10]
            )[0]

            referral_type = random.choice(['self', 'ambulance', 'referral', 'liniya'])
            referral_org = (
                random.choice(org_objects)
                if referral_type in ('referral', 'liniya')
                else None
            )

            mkb_code, mkb_text = random.choice(mkb10_codes)
            district = random.choice(district_objects)
            city = City.objects.filter(district=district).first()
            attending = random.choice(doctor_objects)
            head = random.choice(head_doctors)

            resident_status = random.choices(
                ['resident', 'non_resident'],
                weights=[90, 10]
            )[0]

            passport = (
                f"AB{random.randint(1000000, 9999999)}"
                if resident_status == 'resident'
                else 'NOREZIDENT'
            )

            try:
                patient = PatientCard.objects.create(
                    medical_record_number=record_number,
                    full_name=full_name,
                    gender=gender,
                    birth_date=birth_date,
                    resident_status=resident_status,
                    country=country,
                    region=region,
                    district=district,
                    city=city,
                    street_address=f"{random.choice(kochalar)}, {random.randint(1, 120)}-uy",
                    social_status=random.choice([
                        'employed', 'student_higher', 'student_school', 'unemployed'
                    ]),
                    passport_serial=passport,
                    referral_type=referral_type,
                    referral_organization=referral_org,
                    referring_diagnosis=f"{mkb_code} - {mkb_text}",
                    admission_diagnosis=f"{mkb_code} - {mkb_text}",
                    hours_after_illness=random.choice(['under_6', '7_to_24', 'over_24']),
                    is_emergency=random.choice([True, False]),
                    is_paid=random.choice([True, False]),
                    admission_date=admission_date,
                    department=random.choice(dept_objects),
                    admission_count=random.choice(['first', 'repeated']),
                    days_in_hospital=days,
                    outcome=outcome,
                    discharge_date=discharge_date,
                    clinical_main_diagnosis=mkb_code,
                    clinical_main_diagnosis_text=mkb_text,
                    clinical_comorbidities=random.choice([
                        "", "Gipertoniya", "Qandli diabet", "Semizlik", ""
                    ]),
                    pathological_main_diagnosis=mkb_code if outcome == 'deceased' else '',
                    pathological_main_diagnosis_text=mkb_text if outcome == 'deceased' else '',
                    aids_test_date=admission_date.date(),
                    aids_test_result=random.choice(['Manfiy', 'Manfiy', 'Musbat']),
                    wp_test_date=admission_date.date(),
                    wp_test_result=random.choice(['Manfiy', 'Manfiy', 'Musbat']),
                    is_war_veteran=random.choices([True, False], weights=[10, 90])[0],
                    attending_doctor=attending,
                    department_head=head,
                )

                # O'lim sababi
                if outcome == 'deceased':
                    DeathCause.objects.create(
                        patient_card=patient,
                        immediate_cause=f"{mkb_text} asoratlari",
                        underlying_cause=mkb_text,
                        main_disease_code=mkb_code,
                        other_significant_conditions=random.choice([
                            "", "Gipertoniya kasalligi", "Qandli diabet 2-tur", ""
                        ])
                    )

                # Jarrohlik amaliyotlari (30% ehtimol)
                if random.random() < 0.3:
                    SurgicalOperation.objects.create(
                        patient_card=patient,
                        operation_date=(
                            admission_date + timedelta(days=random.randint(0, 3))
                        ).date(),
                        operation_name=random.choice(operations_list),
                        complication=random.choice(["", "", "Qon ketish", "Infeksiya"])
                    )

                created += 1

            except Exception as e:
                skipped += 1
                self.stdout.write(self.style.WARNING(f"  Xato: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ {created} ta bemor kartasi yaratildi!"
            f"\n⚠️  {skipped} ta o'tkazib yuborildi"
            f"\n📋 Bo'limlar: {len(dept_objects)}"
            f"\n👨‍⚕️ Shifokorlar: {len(doctor_objects)}"
            f"\n🏢 Tashkilotlar: {len(org_objects)}"
        ))