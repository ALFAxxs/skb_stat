import re

import pandas as pd
from django.core.management.base import BaseCommand

from apps.patients.models import ICD10Code

LEAF_CODE_RE = re.compile(r'^[A-Z]\d{2}(\.\d{1,3})?[+*]?$')
RANGE_CODE_RE = re.compile(r'^[A-Z]\d{2}-[A-Z]\d{2}$')


def clean(value):
    if pd.isna(value):
        return ''
    return re.sub(r'\s+', ' ', str(value)).strip()


class Command(BaseCommand):
    help = "MKB-10 kodlarini Excel fayldan (har bir varaqda Kod/Nomi(O'zbekcha)/Название(Русский) ustunlari) import qilish"

    def add_arguments(self, parser):
        parser.add_argument('xlsx_file', type=str)

    def handle(self, *args, **options):
        xls = pd.ExcelFile(options['xlsx_file'])

        entries = {}
        for sheet in xls.sheet_names:
            df = xls.parse(sheet, header=None)
            for _, row in df.iterrows():
                values = list(row)
                code = clean(values[0])
                if not code or code == 'Kod' or RANGE_CODE_RE.match(code):
                    continue
                if not LEAF_CODE_RE.match(code):
                    continue
                rest = [v for v in values[1:] if not pd.isna(v) and str(v).strip() != '']
                if len(rest) < 2:
                    continue
                entries[code] = (clean(rest[0]), clean(rest[-1]))

        created = 0
        updated = 0
        for code, (title_uz, title_ru) in entries.items():
            obj, is_new = ICD10Code.objects.update_or_create(
                code=code,
                defaults={
                    'title_uz': title_uz,
                    'title_ru': title_ru,
                    'category': code[:3],
                }
            )
            if is_new:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f"{created} ta yangi kod qo'shildi, {updated} ta kod yangilandi (jami {len(entries)})."
        ))
