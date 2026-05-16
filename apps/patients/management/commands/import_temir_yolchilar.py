# apps/patients/management/commands/import_temir_yolchilar.py
# v2 — jinsi, kim tomonidan keltirilgan, ijtimoiy xolati ustunlari qo'shildi
#
# Ishlatish:
#   python manage.py import_temir_yolchilar --file /path/to/Temir_yolchilar.xlsx
#   python manage.py import_temir_yolchilar --file /path/to/Temir_yolchilar.xlsx --dry-run
#   python manage.py import_temir_yolchilar --file /path/to/Temir_yolchilar.xlsx --skip-duplicates

import uuid
import pandas as pd
from datetime import datetime, date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from apps.patients.models import (
    PatientCard, Department, Organization, Country
)


# Excel jinsi → model GENDER_CHOICES
GENDER_MAP = {
    'm': 'M', 'м': 'M', 'erkak': 'M', 'male': 'M', 'муж': 'M',
    'f': 'F', 'ж': 'F', 'ayol': 'F', 'female': 'F', 'жен': 'F',
}

# Excel ijtimoiy xolati → model SOCIAL_STATUS_CHOICES
SOCIAL_MAP = {
    'ishlaydi':              'employed',
    'ishlamaydi':            'unemployed',
    'ishsiz':                'unemployed',
    'pensioner':             'pensioner',
    'pensiya':               'pensioner',
    'student':               'student_higher',
    "o'quvchi":              'student_school',
    'oquvchi':               'student_school',
    'qaramogida':            'dependent',
    "ota-ona qaramog'ida":   'dependent',
}

# Excel kim tomonidan keltirilgan → model REFERRAL_TYPE_CHOICES
REFERRAL_MAP = {
    "o'zi":       'self',
    'ozi':        'self',
    'self':       'self',
    'tez yordam': 'ambulance',
    'tez tibbiy': 'ambulance',
    'ambulance':  'ambulance',
    "yo'llanma":  'referral',
    'yollanma':   'referral',
    'referral':   'referral',
    'liniya':     'liniya',
    'линия':      'liniya',
}

# Excel bo'lim nomi → DB da saqlangan nom
DEPT_MAP = {
    'ichki kasalliklari':        'ichki kasalliklari',
    'yurak kasallilari':         'yurak kasallilari',
    'yurak kasalliklari':        'yurak kasallilari',
    'reanimatsiya':              'Reanimatsiya',
    'jarrohlik':                 'Jarrohlik',
    "me'da ichak kasalliklari":  "Me'da ichak kasalliklari",
    "lor bo'limi":               "LOR bo'limi",
    "ko'z kasalliklari":         "Ko'z kasalliklari",
    'asab kasalliklari':         'asab kasalliklari',
    'ginekologiya':              'Ginekologiya',
}


def clean_str(val, default=''):
    if pd.isna(val):
        return default
    return str(val).strip()


def parse_date(val):
    if pd.isna(val):
        return None
    if isinstance(val, (datetime, pd.Timestamp)):
        try:
            d = val.date() if hasattr(val, 'date') else val
            if d.year < 1900 or d.year > 2100:
                return None
            return d
        except Exception:
            return None
    if isinstance(val, date):
        return val
    try:
        return pd.to_datetime(str(val), dayfirst=False).date()
    except Exception:
        return None


def gen_record_number():
    year = timezone.now().year
    while True:
        num = f"TY-{year}-{str(uuid.uuid4())[:6].upper()}"
        if not PatientCard.objects.filter(medical_record_number=num).exists():
            return num


class Command(BaseCommand):
    help = "Excel fayldan temir yo'lchi bemorlarni tizimga import qilish"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', required=True,
            help="Excel fayl yo'li"
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Haqiqatda saqlamasdan tekshirish rejimi"
        )
        parser.add_argument(
            '--skip-duplicates', action='store_true',
            help="Passport seriyasi mavjud bo'lsa o'tkazib yuborish"
        )
        parser.add_argument(
            '--sheet', default=0,
            help="Excel sheet nomi yoki indeksi (default: 0)"
        )

    def handle(self, *args, **options):
        filepath   = options['file']
        dry_run    = options['dry_run']
        skip_dupes = options['skip_duplicates']

        if dry_run:
            self.stdout.write(self.style.WARNING("⚠️  DRY-RUN rejimi — hech narsa saqlanmaydi\n"))

        try:
            df = pd.read_excel(filepath, sheet_name=options['sheet'])
        except FileNotFoundError:
            raise CommandError(f"Fayl topilmadi: {filepath}")
        except Exception as e:
            raise CommandError(f"Faylni o'qishda xato: {e}")

        self.stdout.write(f"📄 Jami {len(df)} qator topildi.\n")

        uzbekistan, _ = Country.objects.get_or_create(name="O'zbekiston")

        created_count = 0
        skipped_count = 0
        error_count   = 0
        errors_log    = []

        for idx, row in df.iterrows():
            excel_row = idx + 2

            full_name  = clean_str(row.get('F.I.SH'))
            passport   = clean_str(row.get('passport seriya'))
            jshshir    = clean_str(row.get('JSHSHIR'))
            if jshshir and '.' in jshshir:
                jshshir = jshshir.split('.')[0]
            if jshshir and jshshir.replace('0', '') == '':
                jshshir = ''

            birth_date     = parse_date(row.get('tugilgan sana'))
            admission_date = parse_date(row.get('sana'))
            address        = clean_str(row.get('doimiy yashash joyi'))
            workplace_name = clean_str(row.get('ish joyi/ yuborilgan muassasasi'))
            position       = clean_str(row.get('lavozimi'))
            diagnosis      = clean_str(row.get('qabulxona tashxisi'))
            dept_name_raw  = clean_str(row.get('bemor yotqizilgan bolim'))

            # --- Yangi ustunlar (v2) ---
            gender_raw   = clean_str(row.get('jinsi')).lower()
            referral_raw = clean_str(row.get('kim tomonidan keltirilgan')).lower()
            social_raw   = clean_str(row.get('ijtimoiy xolati')).lower()

            # --- Majburiy maydon ---
            if not full_name:
                errors_log.append(f"  Qator {excel_row}: Ism-familiya bo'sh — o'tkazildi")
                error_count += 1
                continue

            # --- Dublikat tekshiruv ---
            if passport:
                existing = PatientCard.objects.filter(passport_serial=passport).first()
                if existing:
                    if skip_dupes:
                        skipped_count += 1
                        self.stdout.write(
                            f"  Qator {excel_row}: {full_name} — "
                            f"passport {passport} mavjud, o'tkazildi."
                        )
                        continue
                    else:
                        errors_log.append(
                            f"  Qator {excel_row}: {full_name} — "
                            f"passport {passport} allaqachon mavjud (ID: {existing.pk}). "
                            f"--skip-duplicates flagini ishlating."
                        )
                        error_count += 1
                        continue

            # --- Jins (ustundan, keyin ismdan fallback) ---
            gender = GENDER_MAP.get(gender_raw)
            if not gender:
                name_lower = full_name.lower()
                female_endings = ['ona', 'ova', 'ovna', 'evna', 'евна', 'овна', 'ова']
                gender = 'F' if any(name_lower.endswith(e) for e in female_endings) else 'M'

            # --- Ijtimoiy holat ---
            social_status = SOCIAL_MAP.get(social_raw, 'employed')
            is_pensioner  = (social_status == 'pensioner')

            # --- Kim keltirgan ---
            referral_type = REFERRAL_MAP.get(referral_raw, '')
            # 'liniya' model da REFERRAL_TYPE_CHOICES da bor — to'g'ridan saqlash mumkin

            # --- Bo'lim ---
            department = None
            if dept_name_raw:
                canonical = DEPT_MAP.get(dept_name_raw.lower(), dept_name_raw)
                department, _ = Department.objects.get_or_create(
                    name__iexact=canonical,
                    defaults={'name': canonical, 'is_active': True}
                )

            # --- Ish joyi ---
            workplace_org = None
            if workplace_name:
                workplace_org, _ = Organization.objects.get_or_create(
                    enterprise_name=workplace_name,
                    branch_name='',
                    defaults={'is_active': True}
                )

            # --- Admission datetime ---
            if admission_date:
                adm_dt = timezone.make_aware(
                    datetime.combine(admission_date, datetime.min.time())
                )
            else:
                adm_dt = timezone.now()

            # --- Saqlash ---
            if not dry_run:
                try:
                    with transaction.atomic():
                        patient = PatientCard(
                            medical_record_number = gen_record_number(),
                            full_name             = full_name,
                            gender                = gender,
                            birth_date            = birth_date,
                            passport_serial       = passport,
                            JSHSHIR               = jshshir,
                            street_address        = address,
                            workplace_org         = workplace_org,
                            position              = position,
                            admission_diagnosis   = diagnosis,
                            referring_diagnosis   = '',
                            department            = department,
                            admission_date        = adm_dt,
                            patient_category      = 'railway',
                            social_status         = social_status,
                            is_pensioner          = is_pensioner,
                            referral_type         = referral_type,
                            status                = 'admitted',
                            country               = uzbekistan,
                            visit_type            = 'inpatient',
                        )
                        patient.save()
                        created_count += 1
                        self.stdout.write(
                            f"  ✅ Qator {excel_row}: {full_name} | "
                            f"{gender} | {social_status} | {referral_type} — saqlandi (ID: {patient.pk})"
                        )
                except Exception as e:
                    errors_log.append(f"  Qator {excel_row}: {full_name} — xato: {e}")
                    error_count += 1
            else:
                self.stdout.write(
                    f"  [DRY] Qator {excel_row}: {full_name} | "
                    f"jins: {gender} | ijtimoiy: {social_status} | "
                    f"keltirgan: {referral_type or referral_raw!r} | bo'lim: {dept_name_raw}"
                )
                created_count += 1

        # --- Natija ---
        self.stdout.write("\n" + "=" * 55)
        self.stdout.write(self.style.SUCCESS(f"✅ Yaratildi:    {created_count}"))
        self.stdout.write(self.style.WARNING(f"⏭️  O'tkazildi:   {skipped_count}"))
        self.stdout.write(self.style.ERROR(  f"❌ Xatolar:      {error_count}"))

        if errors_log:
            self.stdout.write("\n📋 Xato tafsilotlari:")
            for line in errors_log:
                self.stdout.write(self.style.ERROR(line))

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  Bu DRY-RUN edi. Haqiqatda saqlash uchun --dry-run ni olib tashlang."
            ))

