# apps/services/management/commands/import_medicines.py

from django.core.management.base import BaseCommand
from openpyxl import load_workbook


class Command(BaseCommand):
    help = "Dori-darmonlarni Excel fayldan import qilish"

    def add_arguments(self, parser):
        parser.add_argument('filepath', type=str, help="Excel fayl yo'li")
        parser.add_argument(
            '--sheet', type=str, default=None,
            help="Sheet nomi (belgilanmasa — birinchi sheet)"
        )
        parser.add_argument(
            '--skip-header', action='store_true', default=True,
            help="Birinchi qatorni sarlavha sifatida o'tkazib yuborish"
        )

    def handle(self, *args, **options):
        from apps.services.models import Medicine

        filepath = options['filepath']
        sheet_name = options.get('sheet')

        try:
            wb = load_workbook(filepath, read_only=True)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Fayl ochilmadi: {e}"))
            return

        ws = wb[sheet_name] if sheet_name else wb.active
        self.stdout.write(f"Sheet: '{ws.title}'")

        # Birliklar standartlashtirilgan ro'yxat
        UNIT_MAP = {
            'qadoq': 'dona', 'пар': 'dona', 'рул': 'dona',
            'к-т': 'dona', 'К-т': 'dona', 'тюб': 'tuba',
            'flakon': 'shisha', 'flakon ': 'shisha',
            'доз/ampula': 'ampula', 'канис': 'shisha',
            'литр': 'l', 'kub.metr': 'l', 'kg': 'g',
            "nabor/to'plam": 'dona', ' ': 'dona', '': 'dona',
        }

        ALLOWED_UNITS = {
            'dona', 'ml', 'mg', 'g', 'l', 'ampula',
            'kapsula', 'tabletka', 'paket', 'shisha', 'tuba',
        }

        created = 0
        skipped = 0
        errors  = 0

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), 2):
            name = row[0] if row[0] else None
            unit = row[1] if len(row) > 1 and row[1] else 'dona'

            if not name or not str(name).strip():
                skipped += 1
                continue

            name = str(name).strip()
            unit = str(unit).strip()

            # Birlikni standartlashtirish
            unit = UNIT_MAP.get(unit, unit)
            if unit not in ALLOWED_UNITS:
                unit = 'dona'

            try:
                obj, is_new = Medicine.objects.get_or_create(
                    name=name,
                    defaults={'unit': unit, 'is_active': True}
                )
                if is_new:
                    created += 1
                    if created <= 5:
                        self.stdout.write(
                            self.style.SUCCESS(f"  + {name} ({unit})")
                        )
                else:
                    skipped += 1

            except Exception as e:
                errors += 1
                self.stderr.write(f"  Qator {row_num} xato: {e}")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"✅ Yakunlandi: {created} ta qo'shildi, "
            f"{skipped} ta o'tkazildi, {errors} ta xato"
        ))