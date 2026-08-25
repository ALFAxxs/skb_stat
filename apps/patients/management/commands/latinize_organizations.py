# apps/patients/management/commands/latinize_organizations.py

from django.core.management.base import BaseCommand
from apps.patients.models import Organization
from apps.patients.transliteration import cyrillic_to_latin, has_cyrillic


class Command(BaseCommand):
    help = (
        "Organization jadvalidagi enterprise_name/branch_name maydonlaridagi "
        "kirillcha matnni lotinga o'giradi. Standart holatda faqat "
        "ko'rsatadi (dry-run) — saqlash uchun --apply bering."
    )

    def add_arguments(self, parser):
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

        changes = []
        for org in Organization.objects.all().order_by('pk'):
            new_ent = cyrillic_to_latin(org.enterprise_name)
            new_branch = cyrillic_to_latin(org.branch_name)
            if new_ent != org.enterprise_name or new_branch != org.branch_name:
                changes.append((org, new_ent, new_branch))

        total_with_cyrillic = sum(
            1 for o in Organization.objects.all()
            if has_cyrillic(o.enterprise_name) or has_cyrillic(o.branch_name)
        )

        self.stdout.write(f"Jami Organization yozuvlar: {Organization.objects.count()} ta")
        self.stdout.write(f"Kirill harf(lar)i borligi aniqlangan: {total_with_cyrillic} ta")
        self.stdout.write(f"O'zgaradigan yozuvlar: {len(changes)} ta\n")

        shown = changes[:limit] if limit else changes
        for org, new_ent, new_branch in shown:
            if new_ent != org.enterprise_name:
                self.stdout.write(f"  [{org.pk}] enterprise_name:")
                self.stdout.write(f"      - {org.enterprise_name}")
                self.stdout.write(f"      + {new_ent}")
            if new_branch != org.branch_name:
                self.stdout.write(f"  [{org.pk}] branch_name:")
                self.stdout.write(f"      - {org.branch_name}")
                self.stdout.write(f"      + {new_branch}")

        if not apply_changes:
            self.stdout.write(self.style.WARNING(
                "\nBu dry-run edi — hech narsa saqlanmadi. "
                "Natijalarni tekshirib bo'lgach --apply bilan ishga tushiring."
            ))
            return

        to_apply = changes[:limit] if limit else changes
        for org, new_ent, new_branch in to_apply:
            org.enterprise_name = new_ent
            org.branch_name = new_branch
        Organization.objects.bulk_update(
            [org for org, _, _ in to_apply], ['enterprise_name', 'branch_name']
        )
        self.stdout.write(self.style.SUCCESS(
            f"\n{len(to_apply)} ta yozuv lotinga o'girildi va saqlandi."
        ))
