# apps/services/management/commands/import_services.py

import pandas as pd
from django.core.management.base import BaseCommand
from apps.services.models import ServiceCategory, Service


CATEGORIES = {
    (4, 102):   ('lab',          '🔬 Laboratoriya'),
    (103, 157): ('radiology',    '📷 Rentgen'),
    (158, 193): ('radiology',    '🔊 UZI/Ultratovush'),
    (194, 203): ('radiology',    '❤️ Kardiologiya tekshiruvlari'),
    (204, 227): ('physio',       '⚡ Fizioterapiya'),
    (228, 245): ('consultation', '👨‍⚕️ Konsultatsiya'),
    (246, 251): ('other',        '🩺 Muolajalar'),
    (252, 253): ('lab',          '🩸 Qon guruhi'),
    (254, 269): ('other',        '👂 LOR muolajalar'),
    (270, 302): ('surgery',      '✂️ LOR jarrohlik'),
    (303, 323): ('other',        '👁️ Ko\'z tekshiruvlari'),
    (324, 345): ('surgery',      '✂️ Ko\'z jarrohlik'),
    (346, 372): ('surgery',      '✂️ Ginekologiya jarrohlik'),
    (373, 377): ('other',        '👩‍⚕️ Ginekologiya muolajalar'),
    (378, 513): ('surgery',      '✂️ Umumiy jarrohlik'),
    (514, 566): ('surgery',      '✂️ Travmatologiya'),
    (567, 588): ('other',        '🦴 Gips va blokadalar'),
    (589, 608): ('other',        '💄 Kosmetologiya'),
    (609, 611): ('other',        '🩸 Plazmaferez'),
    (612, 615): ('other',        '💉 Inyeksiyalar'),
    (616, 617): ('other',        '🏠 Uyga chaqiruv'),
    (618, 621): ('other',        '🧰 Sterilizatsiya'),
    (622, 667): ('radiology',    '🧲 MRT'),
    (668, 676): ('other',        '🛏️ Yotoq-joy'),
}


class Command(BaseCommand):
    help = 'Excel fayldan xizmatlarni import qilish'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            nargs='?',
            default='xizmatlar.xlsx',
            help='Excel fayl yo\'li (default: xizmatlar.xlsx)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Import oldidan barcha xizmatlarni o\'chirish'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']

        if options['clear']:
            Service.objects.all().delete()
            ServiceCategory.objects.all().delete()
            self.stdout.write('Barcha xizmatlar o\'chirildi.')

        # Excel faylni o'qish
        try:
            df = pd.read_excel(file_path, header=None)
        except FileNotFoundError:
            self.stderr.write(f'Fayl topilmadi: {file_path}')
            return

        df.columns = ['name', 'price_normal', 'price_nonresident']

        total_cats = 0
        total_services = 0

        for (start, end), (cat_type, cat_name) in CATEGORIES.items():
            # Kategoriya ikonasini ajratib olish
            icon = cat_name.split()[0] if cat_name else '🏥'
            name_only = ' '.join(cat_name.split()[1:])

            cat, cat_created = ServiceCategory.objects.get_or_create(
                name=name_only,
                defaults={
                    'category_type': cat_type,
                    'icon': icon,
                    'is_active': True,
                }
            )
            if cat_created:
                total_cats += 1

            # Xizmatlarni qo'shish
            rows = df.iloc[start:end].dropna(subset=['name'])
            for _, row in rows.iterrows():
                name = str(row['name']).strip().replace('\n', ' ').replace('\r', '')
                if not name or name in ('nan', 'NaN', ''):
                    continue

                try:
                    price_normal = int(float(row['price_normal'])) \
                        if pd.notna(row['price_normal']) else 0
                    price_nonresident = int(float(row['price_nonresident'])) \
                        if pd.notna(row['price_nonresident']) else 0
                except (ValueError, TypeError):
                    price_normal = 0
                    price_nonresident = 0

                # Norezident narxi = oddiy * 1.25 bo'lishi kerak
                # Lekin temir yo'lchi uchun alohida narx yo'q — price_normal dan foydalanamiz
                svc, svc_created = Service.objects.get_or_create(
                    name=name,
                    category=cat,
                    defaults={
                        'price_normal': price_normal,
                        'price_railway': price_normal,  # Temir yo'lchi = oddiy narx
                        'is_active': True,
                    }
                )
                if not svc_created:
                    # Narxni yangilash
                    svc.price_normal = price_normal
                    svc.price_railway = price_normal
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