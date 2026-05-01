# apps/statistic/views.py

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth
from apps.patients.models import (
    PatientCard, Department, Doctor,
    Organization, HospitalType
)
from apps.users.decorators import role_required
import json


@login_required
@role_required('admin', 'statistician', 'doctor', 'viewer')
def statistics_dashboard(request):

    # ==================== FILTERLAR ====================
    year = request.GET.get('year', '')
    month = request.GET.get('month', '')
    department_id = request.GET.get('department', '')
    doctor_id = request.GET.get('doctor', '')
    outcome = request.GET.get('outcome', '')
    status = request.GET.get('status', '')
    gender = request.GET.get('gender', '')
    patient_category = request.GET.get('patient_category', '')
    resident_status = request.GET.get('resident_status', '')
    referral_type = request.GET.get('referral_type', '')
    org_id = request.GET.get('org', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    age_group = request.GET.get('age_group', '')  # under16 / adult

    qs = PatientCard.objects.all()

    # Bo'lim bo'yicha cheklash (rol asosida)
    from apps.users.decorators import department_filter
    qs = department_filter(qs, request.user)

    # Filterlarni qo'llash
    if year:
        qs = qs.filter(admission_date__year=year)
    if month:
        qs = qs.filter(admission_date__month=month)
    if department_id:
        qs = qs.filter(department_id=department_id)
    if doctor_id:
        qs = qs.filter(attending_doctor_id=doctor_id)
    if outcome:
        qs = qs.filter(outcome=outcome)
    if status:
        qs = qs.filter(status=status)
    if gender:
        qs = qs.filter(gender=gender)
    if patient_category:
        qs = qs.filter(patient_category=patient_category)
    if resident_status:
        qs = qs.filter(resident_status=resident_status)
    if referral_type:
        qs = qs.filter(referral_type=referral_type)
    if org_id:
        qs = qs.filter(workplace_org_id=org_id)
    if date_from:
        qs = qs.filter(admission_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(admission_date__date__lte=date_to)

    from datetime import date as _date
    from dateutil.relativedelta import relativedelta as _rd
    cutoff_16 = _date.today() - _rd(years=16)

    # Yosh guruhi filtri — Python da hisoblash (SQLite strftime muammosini chetlab)
    from datetime import date
    if age_group in ('under16', 'adult'):
        from apps.patients.models import PatientCard as PC
        def calc_age_at_admission(p):
            if not p.birth_date or not p.admission_date:
                return None
            adm = p.admission_date.date() if hasattr(p.admission_date, 'date') else p.admission_date
            b = p.birth_date
            age = adm.year - b.year - ((adm.month, adm.day) < (b.month, b.day))
            return age
        # Avval birth_date va admission_date bor bemorlarni olish
        qs = qs.filter(birth_date__isnull=False, admission_date__isnull=False)
        pks = []
        for p in qs.only('pk', 'birth_date', 'admission_date'):
            age = calc_age_at_admission(p)
            if age is None:
                continue
            if age_group == 'under16' and age < 16:
                pks.append(p.pk)
            elif age_group == 'adult' and age >= 16:
                pks.append(p.pk)
        qs = qs.filter(pk__in=pks)

    # ==================== UMUMIY SONLAR ====================
    total = qs.count()
    discharged = qs.filter(outcome='discharged').count()
    deceased = qs.filter(outcome='deceased').count()
    transferred = qs.filter(outcome='transferred').count()
    registered = qs.filter(status='registered').count()
    admitted = qs.filter(status='admitted').count()
    completed = qs.filter(status='completed').count()
    emergency_count = qs.filter(is_emergency=True).count()
    non_emergency_count = qs.filter(is_emergency=False).count()
    resident_count = qs.filter(resident_status='resident').count()
    non_resident_count = qs.filter(resident_status='non_resident').count()
    avg_days = qs.aggregate(avg=Avg('days_in_hospital'))['avg'] or 0

    # ==================== JINS BO'YICHA ====================
    gender_stats = qs.values('gender').annotate(count=Count('id'))
    gender_data = {'M': 0, 'F': 0}
    for item in gender_stats:
        if item['gender'] in gender_data:
            gender_data[item['gender']] = item['count']

    # ==================== BO'LIM BO'YICHA ====================
    dept_stats = [
        item for item in
        qs.values('department__name').annotate(count=Count('id')).order_by('-count')
        if item['department__name']
    ]

    # ==================== SHIFOKOR BO'YICHA ====================
    doctor_stats = [
        item for item in
        qs.values('attending_doctor__full_name').annotate(count=Count('id')).order_by('-count')[:10]
        if item['attending_doctor__full_name']
    ]

    # ==================== KATEGORIYA BO'YICHA ====================
    category_stats = qs.values('patient_category').annotate(count=Count('id'))
    category_data = {
        'railway': 0, 'paid': 0,
        'non_resident': 0,
    }
    for item in category_stats:
        if item['patient_category'] in category_data:
            category_data[item['patient_category']] = item['count']

    # ==================== OYLIK DINAMIKA ====================
    monthly_stats = (
        qs.annotate(month=TruncMonth('admission_date'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    monthly_labels = [
        item['month'].strftime('%Y-%m')
        for item in monthly_stats if item['month']
    ]
    monthly_values = [
        item['count']
        for item in monthly_stats if item['month']
    ]

    # ==================== TASHKILOT BO'YICHA ====================
    from apps.services.models import PatientService
    from django.db.models import Sum

    org_stats = (
        qs.filter(workplace_org__isnull=False)
        .values(
            'workplace_org__id',
            'workplace_org__enterprise_name',
            'workplace_org__branch_name',
            'workplace_org__enterprise_code',
            'workplace_org__branch_code',
        )
        .annotate(
            patient_count=Count('id'),
        )
        .order_by('-patient_count')
    )

    # Har bir tashkilot uchun xizmatlar summasi
    org_ids = [o['workplace_org__id'] for o in org_stats]
    org_service_totals = {}
    if org_ids:
        svc_agg = (
            PatientService.objects
            .filter(patient_card__workplace_org_id__in=org_ids)
            .values('patient_card__workplace_org_id')
            .annotate(total=Sum('price'))
        )
        for s in svc_agg:
            org_service_totals[s['patient_card__workplace_org_id']] = float(s['total'] or 0)

    # org_stats ga xizmat summasi qo'shish
    org_stats_list = []
    for o in org_stats:
        org_id = o['workplace_org__id']
        name = o['workplace_org__enterprise_name'] or ''
        branch = o['workplace_org__branch_name'] or ''
        org_stats_list.append({
            'id': org_id,
            'name': f"{name} — {branch}" if branch else name,
            'enterprise_code': o['workplace_org__enterprise_code'] or '',
            'branch_code': o['workplace_org__branch_code'] or '',
            'patient_count': o['patient_count'],
            'service_total': org_service_totals.get(org_id, 0),
        })

    # Tashkilot bo'yicha bo'lim taqsimoti (top tashkilot uchun)
    org_dept_stats = []
    if org_stats_list:
        top_org_id = org_stats_list[0]['id']
        org_dept_stats = list(
            qs.filter(workplace_org_id=top_org_id)
            .values('department__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )

    # ==================== DORI STATISTIKASI ====================
    from apps.services.models import PatientMedicine
    from django.db.models import Sum as DSum

    # Eng ko'p ishlatiladigan dorilar TOP-15
    top_medicines = (
        PatientMedicine.objects
        .filter(patient_card__in=qs)
        .values('medicine__name', 'medicine__unit')
        .annotate(
            total_qty=DSum('quantity'),
            total_sum=DSum('price'),
            patient_count=Count('patient_card', distinct=True),
        )
        .order_by('-total_sum')[:15]
    )

    # Umumiy dori xarajati
    medicines_grand_total = (
        PatientMedicine.objects
        .filter(patient_card__in=qs)
        .aggregate(t=DSum('price'))['t'] or 0
    )

    # Umumiy xizmat + dori jami
    from decimal import Decimal
    from apps.services.models import PatientService as PS
    services_grand_total = sum(
        float(ps.price) * ps.quantity
        for ps in PS.objects.filter(patient_card__in=qs)
    ) if qs.exists() else 0

    # ==================== IJTIMOIY HOLAT ====================
    social_stats = (
        qs.values('social_status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    # ==================== FILTER UCHUN RO'YXATLAR ====================
    years = [d.year for d in PatientCard.objects.exclude(
        admission_date=None
    ).dates('admission_date', 'year', order='DESC')]

    if request.user.is_superuser or request.user.role == 'admin':
        departments = Department.objects.filter(is_active=True)
        doctors = Doctor.objects.filter(is_active=True).select_related('department')
    else:
        departments = Department.objects.filter(
            pk=request.user.department.pk
        ) if request.user.department else Department.objects.none()
        doctors = Doctor.objects.filter(
            is_active=True,
            department=request.user.department
        ) if request.user.department else Doctor.objects.none()

    # Joriy filter parametrlarini saqlash (Excel uchun)
    current_filters = request.GET.urlencode()

    return render(request, 'statistic/dashboard.html', {
        'total': total,
        'discharged': discharged,
        'deceased': deceased,
        'transferred': transferred,
        'registered': registered,
        'admitted': admitted,
        'completed': completed,
        'emergency_count': emergency_count,
        'non_emergency_count': non_emergency_count,
        'resident_count': resident_count,
        'non_resident_count': non_resident_count,
        'avg_days': round(avg_days, 1),

        'gender_data': json.dumps(gender_data),
        'dept_stats': dept_stats,
        'doctor_stats': doctor_stats,
        'category_data': json.dumps(category_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_values': json.dumps(monthly_values),
        'social_stats': social_stats,

        'years': years,
        'departments': departments,
        'doctors': doctors,

        'selected_year': year,
        'selected_month': month,
        'selected_dept': department_id,
        'selected_doctor': doctor_id,
        'selected_outcome': outcome,
        'selected_status': status,
        'selected_gender': gender,
        'selected_category': patient_category,
        'selected_resident': resident_status,
        'selected_referral': referral_type,
        'selected_org': org_id,
        'org_selected_name': Organization.objects.get(pk=org_id).display_name if org_id and Organization.objects.filter(pk=org_id).exists() else '',
        'organizations': Organization.objects.filter(is_active=True).order_by('enterprise_name', 'branch_name'),
        'date_from': date_from,
        'date_to': date_to,
        'current_filters': current_filters,
        'org_stats': org_stats_list,
        'age_group': age_group,
        'under16_count': qs.filter(birth_date__isnull=False, birth_date__gt=cutoff_16).count() if not age_group else None,
        'adult_count':   qs.filter(birth_date__isnull=False, birth_date__lte=cutoff_16).count() if not age_group else None,
        'top_medicines': top_medicines,
        'medicines_grand_total': float(medicines_grand_total),
        'services_grand_total': services_grand_total,
        'org_dept_stats': org_dept_stats,
    })