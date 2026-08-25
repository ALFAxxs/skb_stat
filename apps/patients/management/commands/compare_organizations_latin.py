# apps/patients/management/commands/compare_organizations_latin.py

import csv

from django.core.management.base import BaseCommand
from apps.patients.models import Organization


class Command(BaseCommand):
    help = (
        "data/organizations_latin.csv faylidagi id'larni bazadagi Organization "
        "id'lari bilan solishtiradi — hech narsani o'zgartirmaydi, faqat ko'rsatadi."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', default='data/organizations_latin.csv',
            help="CSV fayl yo'li (standart: data/organizations_latin.csv)"
        )

    def handle(self, *args, **options):
        with open(options['file'], encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))

        file_ids = {int(row['id']) for row in rows}
        db_ids = set(Organization.objects.values_list('pk', flat=True))

        only_in_file = sorted(file_ids - db_ids)
        only_in_db = sorted(db_ids - file_ids)
        matching = file_ids & db_ids

        self.stdout.write(f"Faylda: {len(file_ids)} ta id")
        self.stdout.write(f"Bazada: {len(db_ids)} ta id")
        self.stdout.write(f"Mos keladi: {len(matching)} ta\n")

        if only_in_file:
            self.stdout.write(self.style.WARNING(
                f"Faylda bor, bazada yo'q ({len(only_in_file)} ta): {only_in_file}"
            ))
        else:
            self.stdout.write("Faylda bor, bazada yo'q: yo'q")

        if only_in_db:
            self.stdout.write(self.style.WARNING(
                f"Bazada bor, faylda yo'q ({len(only_in_db)} ta): {only_in_db}"
            ))
            names = list(
                Organization.objects.filter(pk__in=only_in_db)
                .values_list('pk', 'enterprise_name', 'branch_name')
            )
            for pk, ent, branch in names:
                label = f"{ent} — {branch}" if branch else ent
                self.stdout.write(f"    [{pk}] {label}")
        else:
            self.stdout.write("Bazada bor, faylda yo'q: yo'q")
