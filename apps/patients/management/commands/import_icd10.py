# apps/patients/management/commands/import_icd10.py

import csv
from django.core.management.base import BaseCommand
from apps.patients.models import ICD10Code

class Command(BaseCommand):
    help = "MKB-10 kodlarini CSV dan import qilish"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)

    def handle(self, *args, **options):
        with open(options['csv_file'], encoding='utf-8') as f:
            reader = csv.DictReader(f)
            created = 0
            for row in reader:
                obj, is_new = ICD10Code.objects.update_or_create(
                    code=row['code'].strip(),
                    defaults={
                        'title_uz': row.get('title_uz', '').strip(),
                        'title_ru': row.get('title_ru', '').strip(),
                        'category': row['code'][:3],
                    }
                )
                if is_new:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"{created} ta yangi kod qo'shildi."))