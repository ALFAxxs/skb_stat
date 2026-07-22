"""
Background Excel export tasks (Celery + pandas).
"""
import os
import uuid
import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


def _export_dir():
    d = os.path.join(settings.MEDIA_ROOT, 'temp_exports')
    os.makedirs(d, exist_ok=True)
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Xizmatlar hisoboti
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=560,
             name='services.export_services_excel')
def generate_services_excel(self, filters: dict) -> str:
    """
    Xizmatlar ro'yxatini Excel ga eksport qiladi.
    Qaytaradi: fayl nomi (MEDIA_ROOT/temp_exports/ papkasida).
    """
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from apps.services.models import PatientService

    qs = PatientService.objects.exclude(status='cancelled').values(
        'ordered_at',
        'patient_card__full_name',
        'patient_category_at_order',
        'service__category__name',
        'service__name',
        'quantity',
        'price',
        'status',
        'is_paid',
        'ordered_by__first_name',
        'ordered_by__last_name',
        'performed_by__first_name',
        'performed_by__last_name',
        'result',
    )

    if filters.get('date_from'):
        qs = qs.filter(ordered_at__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(ordered_at__date__lte=filters['date_to'])
    if filters.get('category'):
        qs = qs.filter(service__category_id=filters['category'])
    if filters.get('patient_category'):
        qs = qs.filter(patient_category_at_order=filters['patient_category'])
    if filters.get('visit_type'):
        qs = qs.filter(patient_card__visit_type=filters['visit_type'])

    qs = qs.order_by('-ordered_at')

    # pandas orqali yuklab olish (ORM iterator'dan 3-5x tez)
    df = pd.DataFrame.from_records(qs.iterator(chunk_size=2000))

    if df.empty:
        # Bo'sh fayl
        df = pd.DataFrame(columns=[
            '№', 'Sana', 'Bemor', 'Bemor kategoriyasi', 'Kategoriya',
            'Xizmat', 'Miqdori', 'Narx', 'Jami', 'Holat', "To'langan",
            'Buyurtma bergan', 'Bajargan', 'Natija',
        ])
    else:
        cat_display = {
            'railway': "Temir yo'lchi", 'paid': 'Pullik',
            'non_resident': 'Norezident', 'foreign': 'Chet el',
        }
        status_display = {
            'ordered': 'Buyurtma berildi', 'completed': 'Bajarildi',
            'cancelled': 'Bekor qilindi', 'in_progress': 'Jarayonda',
        }

        df['№'] = range(1, len(df) + 1)
        df['Sana'] = df['ordered_at'].dt.tz_convert('Asia/Tashkent').dt.strftime('%d.%m.%Y %H:%M')
        df['Bemor'] = df['patient_card__full_name']
        df['Bemor kategoriyasi'] = df['patient_category_at_order'].map(cat_display).fillna(df['patient_category_at_order'])
        df['Kategoriya'] = df['service__category__name']
        df['Xizmat'] = df['service__name']
        df['Miqdori'] = df['quantity']
        df['Narx'] = df['price'].astype(float)
        df['Jami'] = (df['price'] * df['quantity']).astype(float)
        df['Holat'] = df['status'].map(status_display).fillna(df['status'])
        df["To'langan"] = df['is_paid'].map({True: 'Ha', False: "Yo'q"})
        df['Buyurtma bergan'] = (
            df['ordered_by__first_name'].fillna('') + ' ' +
            df['ordered_by__last_name'].fillna('')
        ).str.strip().replace('', '—')
        df['Bajargan'] = (
            df['performed_by__first_name'].fillna('') + ' ' +
            df['performed_by__last_name'].fillna('')
        ).str.strip().replace('', '—')
        df['Natija'] = df['result'].fillna('—')

        df = df[['№', 'Sana', 'Bemor', 'Bemor kategoriyasi', 'Kategoriya',
                 'Xizmat', 'Miqdori', 'Narx', 'Jami', 'Holat', "To'langan",
                 'Buyurtma bergan', 'Bajargan', 'Natija']]

    filename = f'services_{uuid.uuid4().hex[:12]}.xlsx'
    filepath = os.path.join(_export_dir(), filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name="Xizmatlar ro'yxati", index=False)
        ws = writer.sheets["Xizmatlar ro'yxati"]
        # Ustun kengliklari
        for col_idx, width in enumerate([4, 16, 25, 16, 18, 30, 8, 12, 12, 14, 10, 22, 22, 30], 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        # Sarlavha formatlash
        hf = Font(bold=True, color='FFFFFF', size=10)
        hfill = PatternFill('solid', fgColor='1F4E79')
        center = Alignment(horizontal='center', vertical='center', wrap_text=True)
        brd = Border(left=Side(style='thin'), right=Side(style='thin'),
                     top=Side(style='thin'), bottom=Side(style='thin'))
        for cell in ws[1]:
            cell.font = hf; cell.fill = hfill
            cell.alignment = center; cell.border = brd

    logger.info(f"Xizmatlar Excel yaratildi: {filename}, qatorlar: {len(df)}")
    return filename


# ──────────────────────────────────────────────────────────────────────────────
# Dori-darmonlar hisoboti
# ──────────────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=0, time_limit=600, soft_time_limit=560,
             name='services.export_medicine_excel')
def generate_medicine_excel(self, filters: dict) -> str:
    """Dori-darmonlar ro'yxatini Excel ga eksport qiladi."""
    import pandas as pd
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from apps.services.models import PatientMedicine

    qs = PatientMedicine.objects.values(
        'ordered_at',
        'patient_card__full_name',
        'medicine__name',
        'medicine__unit',
        'quantity',
        'price',
        'ordered_by__first_name',
        'ordered_by__last_name',
    )
    if filters.get('date_from'):
        qs = qs.filter(ordered_at__date__gte=filters['date_from'])
    if filters.get('date_to'):
        qs = qs.filter(ordered_at__date__lte=filters['date_to'])
    if filters.get('medicine'):
        qs = qs.filter(medicine_id=filters['medicine'])
    if filters.get('patient_category'):
        qs = qs.filter(patient_card__patient_category=filters['patient_category'])
    if filters.get('visit_type'):
        qs = qs.filter(patient_card__visit_type=filters['visit_type'])

    qs = qs.order_by('-ordered_at')
    df = pd.DataFrame.from_records(qs.iterator(chunk_size=2000))

    if df.empty:
        df = pd.DataFrame(columns=['№', 'Sana', 'Bemor', 'Dori nomi', 'Birlik', 'Miqdori', 'Narxi', 'Jami', 'Buyurtma bergan'])
    else:
        df['№'] = range(1, len(df) + 1)
        df['Sana'] = df['ordered_at'].dt.tz_convert('Asia/Tashkent').dt.strftime('%d.%m.%Y')
        df['Bemor'] = df['patient_card__full_name']
        df['Dori nomi'] = df['medicine__name']
        df['Birlik'] = df['medicine__unit']
        df['Miqdori'] = df['quantity'].astype(float)
        df['Narxi'] = df['price'].astype(float)
        df['Jami'] = (df['quantity'] * df['price']).astype(float)
        df['Buyurtma bergan'] = (
            df['ordered_by__first_name'].fillna('') + ' ' +
            df['ordered_by__last_name'].fillna('')
        ).str.strip().replace('', '—')
        df = df[['№', 'Sana', 'Bemor', 'Dori nomi', 'Birlik', 'Miqdori', 'Narxi', 'Jami', 'Buyurtma bergan']]

    filename = f'medicine_{uuid.uuid4().hex[:12]}.xlsx'
    filepath = os.path.join(_export_dir(), filename)

    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Dori-darmonlar', index=False)
        ws = writer.sheets['Dori-darmonlar']
        for col_idx, width in enumerate([4, 14, 28, 28, 10, 12, 14, 14, 22], 1):
            ws.column_dimensions[get_column_letter(col_idx)].width = width
        hf = Font(bold=True, color='FFFFFF', size=10)
        hfill = PatternFill('solid', fgColor='856404')
        center = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for cell in ws[1]:
            cell.font = hf; cell.fill = hfill; cell.alignment = center

    logger.info(f"Dori Excel yaratildi: {filename}, qatorlar: {len(df)}")
    return filename
