# apps/patients/management/commands/apply_organizations_latin.py

import csv

from django.core.management.base import BaseCommand, CommandError
from apps.patients.models import Organization

FIELDS = [
    'is_active', 'branch_code', 'branch_name',
    'enterprise_code', 'enterprise_inn', 'enterprise_name',
]


class Command(BaseCommand):
    help = (
        "data/organizations_latin.csv fayldagi (qo'lda lotinga tuzatilgan) "
        "qiymatlar bilan bazadagi Organization yozuvlarini id bo'yicha "
        "YANGILAYDI (o'chirib-qayta-yaratmaydi — PatientCard.workplace_org "
        "kabi bog'lanishlar buzilmasin uchun). Standart holatda dry-run — "
        "saqlash uchun --apply bering."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', default='data/organizations_latin.csv',
            help="CSV fayl yo'li (standart: data/organizations_latin.csv)"
        )
        parser.add_argument(
            '--apply', action='store_true',
            help="O'zgarishlarni bazaga haqiqatan ham yozadi (aks holda faqat ko'rsatadi)"
        )
        parser.add_argument(
            '--limit', type=int, default=None,
            help="Faqat birinchi N ta o'zgaradigan yozuvni ko'rsatish/qo'llash (sinov uchun)"
        )

    def handle(self, *args, **options):
        apply_changes = options['apply']
        limit = options['limit']

        with open(options['file'], encoding='utf-8', newline='') as f:
            rows = list(csv.DictReader(f))

        orgs_by_id = {org.pk: org for org in Organization.objects.all()}

        changes = []
        missing_ids = []
        for row in rows:
            pk = int(row['id'])
            org = orgs_by_id.get(pk)
            if org is None:
                missing_ids.append(pk)
                continue

            new_values = {
                'is_active': row['is_active'].strip() not in ('0', '', 'False', 'false'),
                'branch_code': row['branch_code'].strip(),
                'branch_name': row['branch_name'].strip(),
                'enterprise_code': row['enterprise_code'].strip(),
                'enterprise_inn': row['enterprise_inn'].strip(),
                'enterprise_name': row['enterprise_name'].strip(),
            }
            diffs = {
                field: (getattr(org, field), new_val)
                for field, new_val in new_values.items()
                if getattr(org, field) != new_val
            }
            if diffs:
                changes.append((org, new_values, diffs))

        if missing_ids:
            raise CommandError(
                f"Faylda bor, bazada topilmagan id'lar: {missing_ids}. "
                f"Avval `compare_organizations_latin` bilan tekshiring."
            )

        self.stdout.write(f"Fayldagi yozuvlar: {len(rows)} ta")
        self.stdout.write(f"O'zgaradigan yozuvlar: {len(changes)} ta\n")

        shown = changes[:limit] if limit else changes
        for org, _, diffs in shown:
            self.stdout.write(f"[{org.pk}] {org.enterprise_name} — {org.branch_name}")
            for field, (old, new) in diffs.items():
                self.stdout.write(f"    {field}: {old!r} -> {new!r}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nBu dry-run edi — hech narsa saqlanmadi. "
                "Natijalarni tekshirib bo'lgach --apply bilan ishga tushiring."
            ))
            return

        to_apply = changes[:limit] if limit else changes
        for org, new_values, _ in to_apply:
            for field, val in new_values.items():
                setattr(org, field, val)
        Organization.objects.bulk_update(
            [org for org, _, _ in to_apply], FIELDS
        )
        self.stdout.write(self.style.SUCCESS(
            f"\n{len(to_apply)} ta Organization yozuvi yangilandi."
        ))
