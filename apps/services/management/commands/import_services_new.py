# apps/services/management/commands/import_services.py

import pandas as pd
from django.core.management.base import BaseCommand
from apps.services.models import ServiceCategory, Service


# Kategoriya type xaritasi — nom bo'yicha
CATEGORY_TYPES = {
    'laboratoriya':  'lab',
    'rentgen':       'radiology',
    'diagnostika':   'radiology',
    'funktsianal':   'radiology',
    'fizioterapiya': 'physio',
    'shifokor':      'consultation',
    'ko\'rigi':      'consultation',
    'jarroh':        'surgery',
    'operasiya':     'surgery',
    'ginekolog':     'surgery',
    'travmatolog':   'surgery',
    'ko\'z':         'other',
    'quloq':         'other',
    'lor':           'other',
    'reanimatsiya':  'other',
    'kosmetelog':    'other',
    'yotoq':         'other',
}

CATEGORY_ICONS = {
    'lab':          '🔬',
    'radiology':    '📷',
    'physio':       '⚡',
    'consultation': '👨‍⚕️',
    'surgery':      '✂️',
    'other':        '🏥',
}


def get_category_type(name):
    name_lower = name.lower()
    for keyword, cat_type in CATEGORY_TYPES.items():
        if keyword in name_lower:
            return cat_type
    return 'other'


class Command(BaseCommand):
    help = 'Excel fayldan xizmatlarni import qilish'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            nargs='?',
            default='xizmatlar.xlsx',
            help="Excel fayl yo'li (default: xizmatlar.xlsx)"
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help="Import oldidan barcha xizmatlarni o'chirish"
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        if options['clear']:
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()
            self.stdout.write("Barcha xizmatlar o'chirildi.")

        # Excel faylni o'qish
        try:
            df = pd.read_excel(file_path, header=None)
        except FileNotFoundError:
            self.stderr.write(f'Fayl topilmadi: {file_path}')
            return

        total_cats = 0
        total_services = 0
        current_cat = None

        for idx, row in df.iterrows():
            col0, col1, col2, col3 = (
                row[0] if len(row) > 0 else None,
                row[1] if len(row) > 1 else None,
                row[2] if len(row) > 2 else None,
                row[3] if len(row) > 3 else None,
            )

            # Sarlavha qatori (1-qator va 3-qator)
            if isinstance(col0, str) and col0 in ('Т/r', 'T/r', '1'):
                continue
            if col0 == 1 and col1 == 2:
                continue

            # Kategoriya qatori: birinchi ustun string, qolganlar bo'sh
            if isinstance(col0, str) and pd.isna(col1) if hasattr(pd, 'isna') else col1 is None:
                cat_name = str(col0).strip()
                if not cat_name:
                    continue
                cat_type = get_category_type(cat_name)
                icon = CATEGORY_ICONS.get(cat_type, '🏥')

                current_cat, created = ServiceCategory.objects.get_or_create(
                    name=cat_name,
                    defaults={
                        'category_type': cat_type,
                        'icon': icon,
                        'is_active': True,
                    }
                )
                if created:
                    total_cats += 1
                    self.stdout.write(f'  + Kategoriya: {cat_name}')
                continue

            # Xizmat qatori: col0 raqam, col1 xizmat nomi
            if current_cat is None:
                continue

            if col1 is None or pd.isna(col1) if hasattr(pd, 'isna') else col1 is None:
                continue

            name = str(col1).strip().replace('\n', ' ').replace('\r', '')
            if not name or name in ('nan', 'NaN', '', 'Xizmat turlari'):
                continue

            # Narxlar
            try:
                price_normal = int(float(col2)) if col2 is not None and str(col2) not in ('nan', 'None') else 0
            except (ValueError, TypeError):
                price_normal = 0

            try:
                price_railway = int(float(col3)) if col3 is not None and str(col3) not in ('nan', 'None') else price_normal
            except (ValueError, TypeError):
                price_railway = price_normal

            svc, svc_created = Service.objects.get_or_create(
                name=name,
                category=current_cat,
                defaults={
                    'price_normal':  price_normal,
                    'price_railway': price_railway,
                    'is_active':     True,
                }
            )
            if not svc_created:
                svc.price_normal  = price_normal
                svc.price_railway = price_railway
                svc.save(update_fields=['price_normal', 'price_railway'])

            if svc_created:
                total_services += 1

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ Import yakunlandi!'
            f'\n   Kategoriyalar: {total_cats} ta yangi'
            f'\n   Xizmatlar: {total_services} ta yangi'
            f'\n   Jami kategoriya: {ServiceCategory.objects.count()} ta'
            f'\n   Jami xizmat: {Service.objects.count()} ta'
        ))
