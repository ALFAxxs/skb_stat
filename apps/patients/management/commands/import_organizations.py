# apps/patients/management/commands/import_organizations.py

import pandas as pd
from django.core.management.base import BaseCommand
from apps.patients.models import Organization


class Command(BaseCommand):
    help = "Excel fayldan ishxonalar ro'yxatini import qilish"

    def add_arguments(self, parser):
        parser.add_argument('file_path', help='Excel fayl yoli')
        parser.add_argument(
            '--clear', action='store_true',
            help='Import oldidan barcha ishxonalarni ochirish'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        try:
            df = pd.read_excel(file_path, header=0, dtype=str)
            df = df.fillna('')
            df.columns = [
                'enterprise_code', 'enterprise_inn',
                'enterprise_name', 'branch_code', 'branch_name'
            ]
        except Exception as e:
            self.stderr.write(f'Fayl oquvda xato: {e}')
            return

        # Bosh va sarlavha qatorlarini olib tashlash
        df = df[df['enterprise_name'].str.strip() != '']
        df = df[~df['enterprise_name'].str.contains(
            'Xaridor korxonasi|korxona nomi', case=False, na=False
        )]
        df = df.reset_index(drop=True)
        self.stdout.write(f"Jami qatorlar: {len(df)} ta")

        if options['clear']:
            deleted, _ = Organization.objects.all().delete()
            self.stdout.write(f"Ochirildi: {deleted} ta")

        created = 0
        updated = 0

        def clean(val):
            v = str(val).strip()
            if v in ('nan', 'None', ''):
                return ''
            # Raqamdan .0 ni olib tashlash (85.0 -> 85)
            if v.endswith('.0') and v[:-2].isdigit():
                return v[:-2]
            return v

        for _, row in df.iterrows():
            ent_name = clean(row['enterprise_name'])
            if not ent_name:
                continue

            ent_code    = clean(row['enterprise_code'])
            ent_inn     = clean(row['enterprise_inn'])
            branch_code = clean(row['branch_code'])
            branch_name = clean(row['branch_name'])

            obj, is_created = Organization.objects.get_or_create(
                enterprise_name=ent_name,
                branch_code=branch_code,
                branch_name=branch_name,
                defaults={
                    'enterprise_code': ent_code,
                    'enterprise_inn':  ent_inn,
                    'is_active':       True,
                }
            )

            if is_created:
                created += 1
            else:
                obj.enterprise_code = ent_code
                obj.enterprise_inn  = ent_inn
                obj.is_active       = True
                obj.save(update_fields=['enterprise_code', 'enterprise_inn', 'is_active'])
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'\nImport yakunlandi!'
            f'\n   Yangi: {created} ta'
            f'\n   Yangilandi: {updated} ta'
            f'\n   Jami bazada: {Organization.objects.count()} ta'
        ))