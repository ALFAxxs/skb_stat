from django.views.decorators.http import require_POST
# apps/patients/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from apps.users.decorators import role_required, department_filter
import json
import uuid

from django.utils import timezone

from datetime import timedelta

from .forms import PatientCardForm, DeathCauseForm, SurgicalOperationFormSet, ReceptionForm
from .models import (
    PatientCard, ICD10Code, DischargeConclusion,
    Region, District, City, Village, Country, OperationType,
    Department, Doctor
)


def _find_recent_duplicate(full_name, birth_date, seconds=120):
    """Bir xil ism+tug'ilgan sana bilan so'nggi N soniyada yaratilgan bemor."""
    if not full_name or not birth_date:
        return None
    cutoff = timezone.now() - timedelta(seconds=seconds)
    return PatientCard.objects.filter(
        full_name__iexact=full_name,
        birth_date=birth_date,
        created_at__gte=cutoff,
    ).order_by('-created_at').first()


# ==================== AJAX VIEWS ====================

@login_required
def add_conclusion(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            name = data.get('name', '').strip()
            if not name:
                return JsonResponse({'success': False, 'error': "Nom bo'sh"})
            obj, created = DischargeConclusion.objects.get_or_create(name=name)
            return JsonResponse({
                'success': True,
                'id': obj.id,
                'name': obj.name,
                'created': created
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False, 'error': 'Faqat POST'})


def get_regions(request):
    country_id = request.GET.get('country_id')
    regions = Region.objects.filter(country_id=country_id).values('id', 'name')
    return JsonResponse(list(regions), safe=False)


def get_districts(request):
    region_id = request.GET.get('region_id')
    districts = District.objects.filter(region_id=region_id).values('id', 'name')
    return JsonResponse(list(districts), safe=False)


def get_cities(request):
    district_id = request.GET.get('district_id')
    cities = City.objects.filter(district_id=district_id).values('id', 'name')
    return JsonResponse(list(cities), safe=False)


def get_villages(request):
    district_id = request.GET.get('district_id')
    villages = Village.objects.filter(district_id=district_id).values('id', 'name')
    return JsonResponse(list(villages), safe=False)


def icd10_search(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse([], safe=False)
    results = ICD10Code.objects.filter(
        Q(code__icontains=q) | Q(title_uz__icontains=q)
    )[:15]
    data = [{'code': r.code, 'title': r.title_uz} for r in results]
    return JsonResponse(data, safe=False)


def operation_type_search(request):
    q = request.GET.get('q', '')
    if len(q) < 1:
        results = OperationType.objects.filter(is_active=True)[:20]
    else:
        results = OperationType.objects.filter(
            Q(name__icontains=q) | Q(code__icontains=q),
            is_active=True
        )[:15]
    data = [{'id': r.id, 'name': str(r)} for r in results]
    return JsonResponse(data, safe=False)


# ==================== PATIENT VIEWS ====================

# apps/patients/views.py — patient_list view

@login_required
def patient_list(request):
    qs = PatientCard.objects.select_related(
        'department', 'attending_doctor', 'registered_by'
    ).order_by('-admission_date')

    # Bo'lim filteri
    qs = department_filter(qs, request.user)

    # Qabulxona barcha bemorlarni ko'radi (filtrsiz)

    # Qidiruv
    query = request.GET.get('q', '')
    if query:
        qs = qs.filter(
            Q(full_name__icontains=query) |
            Q(medical_record_number__icontains=query) |
            Q(passport_serial__icontains=query)
        )

    # Status filteri — yakunlangan faqat aniq filter qilinganda chiqadi
    status = request.GET.get('status', '')
    if status:
        qs = qs.filter(status=status)
    else:
        qs = qs.exclude(status='discharged')

    # Yakun filteri
    outcome = request.GET.get('outcome', '')
    if outcome:
        qs = qs.filter(outcome=outcome)

    # Bo'lim filteri (faqat admin)
    dept_filter = request.GET.get('department', '')
    if dept_filter and (request.user.is_superuser or request.user.role == 'admin'):
        qs = qs.filter(department_id=dept_filter)

    # Visit type filteri (ambulator/statsionar)
    visit_type = request.GET.get('visit_type', '')
    if visit_type:
        qs = qs.filter(visit_type=visit_type)

    # Shifokor filteri
    doctor_filter = request.GET.get('doctor', '')
    if doctor_filter:
        qs = qs.filter(attending_doctor_id=doctor_filter)

    # Registrator o'zi qo'shgan bemorlar filteri
    my_patients = request.GET.get('my_patients', '')
    if my_patients and request.user.role == 'reception':
        qs = qs.filter(registered_by=request.user)

    # Bemor kategoriyasi filteri
    category_filter = request.GET.get('category', '')
    if category_filter:
        qs = qs.filter(patient_category=category_filter)

    # Sana filteri
    date_from = request.GET.get('date_from', '')
    date_to   = request.GET.get('date_to', '')
    if date_from:
        qs = qs.filter(admission_date__date__gte=date_from)
    if date_to:
        qs = qs.filter(admission_date__date__lte=date_to)

    # Filter uchun ro'yxatlar
    from .models import Department, Doctor
    if request.user.is_superuser or request.user.role in ('admin', 'reception', 'statistician'):
        departments = Department.objects.filter(is_active=True)
    else:
        departments = Department.objects.filter(
            pk=request.user.department.pk
        ) if request.user.department else Department.objects.none()

    doctors = Doctor.objects.filter(is_active=True).select_related('department')
    if not request.user.is_superuser and request.user.role not in ('admin', 'reception', 'statistician'):
        if request.user.department:
            doctors = doctors.filter(department=request.user.department)

    # Sahifa o'lchami
    per_page = request.GET.get('per_page', '20')
    try:
        per_page = int(per_page)
        if per_page not in (20, 50, 100):
            per_page = 20
    except ValueError:
        per_page = 20

    paginator = Paginator(qs, per_page)
    page = paginator.get_page(request.GET.get('page'))

    return render(request, 'patients/patient_list.html', {
        'page_obj': page,
        'query': query,
        'selected_status': status,
        'selected_visit_type': visit_type,
        'selected_outcome': outcome,
        'selected_dept': dept_filter,
        'selected_doctor': doctor_filter,
        'selected_category': category_filter,
        'selected_date_from': date_from,
        'selected_date_to': date_to,
        'selected_per_page': per_page,
        'my_patients': my_patients,
        'departments': departments,
        'doctors': doctors,
        'total_count': qs.count(),
    })


@login_required
def patient_detail(request, pk):
    patient = get_object_or_404(
        PatientCard.objects.select_related(
            'department', 'attending_doctor', 'department_head',
            'referral_organization', 'country', 'region', 'district',
            'city', 'discharge_conclusion'
        ).prefetch_related('operations__operation_type'),
        pk=pk
    )

    # Bo'lim tekshiruvi
    if not request.user.is_superuser and request.user.role != 'admin':
        if request.user.role == 'reception':
            if patient.registered_by != request.user:
                messages.error(request, "Siz bu bemorni ko'rishga ruxsatingiz yo'q.")
                return redirect('patient_list')
        elif request.user.department and patient.department != request.user.department:
            messages.error(request, "Siz bu bemorni ko'rishga ruxsatingiz yo'q.")
            return redirect('patient_list')

    death_cause = getattr(patient, 'death_cause', None)
    address_parts = filter(None, [
        str(patient.country) if patient.country else '',
        str(patient.region) if patient.region else '',
        str(patient.district) if patient.district else '',
        str(patient.city) if patient.city else '',
        patient.street_address or '',
    ])
    full_address = ', '.join(address_parts) or '—'

    # Xizmatlar va jami narx
    from apps.services.models import PatientService
    from django.db.models import Sum
    patient_services = PatientService.objects.filter(
        patient_card=patient
    ).select_related('service__category', 'ordered_by').order_by('-ordered_at')
    services_total = sum(s.price * s.quantity for s in patient_services) or 0

    # Bemor tarixi — oldingi tashriflar
    prev_visits = []
    if patient.JSHSHIR:
        prev_visits = PatientCard.objects.filter(
            JSHSHIR=patient.JSHSHIR
        ).exclude(pk=patient.pk).order_by('-admission_date')
    elif patient.passport_serial:
        prev_visits = PatientCard.objects.filter(
            passport_serial=patient.passport_serial
        ).exclude(pk=patient.pk).exclude(
            passport_serial=''
        ).order_by('-admission_date')

    # Dorilar
    from apps.services.models import PatientMedicine
    patient_medicines = PatientMedicine.objects.filter(
        patient_card=patient
    ).select_related('medicine', 'ordered_by').order_by('-ordered_at')
    medicines_total = sum(m.total_price for m in patient_medicines) or 0

    grand_total = float(services_total or 0) + float(medicines_total or 0)

    # Ko'chirish tarixi va xizmatlarni davrlarga bo'lib guruhlash
    transfers = list(
        patient.patient_transfers.all().select_related(
            'from_department', 'from_doctor', 'from_dept_head',
            'to_department', 'to_doctor', 'to_dept_head', 'transferred_by'
        ).order_by('transferred_at')
    )

    # Xizmatlarni vaqt bo'yicha tartiblash (ascending)
    all_svc_asc = list(PatientService.objects.filter(
        patient_card=patient
    ).select_related('service__category', 'ordered_by').order_by('ordered_at'))

    transfer_periods = []
    if transfers:
        # Birinchi davr: yotqizilishdan birinchi ko'chirishgacha
        boundaries = [None] + [t.transferred_at for t in transfers]
        for i, t in enumerate(transfers):
            t_start = boundaries[i]
            t_end   = t.transferred_at
            if t_start is None:
                period_svcs = [s for s in all_svc_asc if s.ordered_at < t_end]
            else:
                period_svcs = [s for s in all_svc_asc if t_start <= s.ordered_at < t_end]
            transfer_periods.append({
                'period_num':    i + 1,
                'start':         t_start,
                'end':           t_end,
                'transfer':      t,
                'dept':          t.from_department,
                'doctor':        t.from_doctor,
                'dept_head':     t.from_dept_head,
                'services':      period_svcs,
                'services_total': sum(s.price * s.quantity for s in period_svcs),
            })
        # Oxirgi davr: so'nggi ko'chirishdan hozirga qadar
        last_t = transfers[-1]
        last_svcs = [s for s in all_svc_asc if s.ordered_at >= last_t.transferred_at]
        transfer_periods.append({
            'period_num':    len(transfers) + 1,
            'start':         last_t.transferred_at,
            'end':           None,
            'transfer':      None,
            'dept':          last_t.to_department,
            'doctor':        last_t.to_doctor,
            'dept_head':     last_t.to_dept_head,
            'services':      last_svcs,
            'services_total': sum(s.price * s.quantity for s in last_svcs),
        })

    return render(request, 'patients/patient_detail.html', {
        'patient': patient,
        'death_cause': death_cause,
        'full_address': full_address,
        'patient_services': patient_services,
        'services_total': services_total,
        'patient_medicines': patient_medicines,
        'medicines_total': medicines_total,
        'grand_total': grand_total,
        'prev_visits': prev_visits,
        'departments': Department.objects.filter(is_active=True).order_by('name'),
        'doctors':     Doctor.objects.filter(is_active=True).select_related('department').order_by('department__name', 'full_name'),
        'dept_heads':  Doctor.objects.filter(is_active=True, is_head=True).order_by('full_name'),
        'today':       timezone.localdate(),
        'transfers':   transfers,
        'transfer_periods': transfer_periods,
        'discharge_conclusions': DischargeConclusion.objects.filter(is_active=True).order_by('name'),
        'outcome_choices':  PatientCard.OUTCOME_CHOICES,
        'status_choices':   PatientCard.STATUS_CHOICES,
    })


def get_doctors(request):
    """AJAX — bo'lim bo'yicha shifokorlarni qaytarish"""
    department_id = request.GET.get('department_id')
    if not department_id:
        return JsonResponse([], safe=False)

    from .models import Doctor
    doctors = Doctor.objects.filter(
        department_id=department_id,
        is_active=True
    ).values('id', 'full_name', 'is_head').order_by('-is_head', 'full_name')

    return JsonResponse(list(doctors), safe=False)

@login_required
@role_required('admin', 'doctor', 'statistician')
def patient_card_create(request):
    if request.method == 'POST':
        form = PatientCardForm(request.POST)
        death_form = DeathCauseForm(request.POST)
        surgery_formset = SurgicalOperationFormSet(request.POST)

        is_deceased = request.POST.get('outcome') == 'deceased'
        forms_valid = form.is_valid() and surgery_formset.is_valid()
        if is_deceased:
            forms_valid = forms_valid and death_form.is_valid()

        if forms_valid:
            dup = _find_recent_duplicate(
                form.cleaned_data.get('full_name', ''),
                form.cleaned_data.get('birth_date'),
            )
            if dup:
                messages.warning(request, f"⚠️ Bu bemor 2 daqiqa ichida allaqachon ro'yxatga olingan: {dup.full_name} (#{dup.medical_record_number})")
                return redirect('patient_detail', pk=dup.pk)

            patient = form.save(commit=False)
            if not request.user.is_superuser and request.user.role != 'admin':
                if request.user.department:
                    patient.department = request.user.department
            patient.save()
            form.save_m2m()

            surgeries = surgery_formset.save(commit=False)
            for s in surgeries:
                s.patient_card = patient
                s.save()
            for s in surgery_formset.deleted_objects:
                s.delete()

            if is_deceased:
                death = death_form.save(commit=False)
                death.patient_card = patient
                death.save()

            messages.success(request, "Bemor kartasi saqlandi!")
            return redirect('patient_list')
        else:
            messages.error(request, "Formada xatoliklar bor. Tekshiring.")
    else:
        form = PatientCardForm()
        if not request.user.is_superuser and request.user.role != 'admin':
            if request.user.department:
                form.initial['department'] = request.user.department
        death_form = DeathCauseForm()
        surgery_formset = SurgicalOperationFormSet()

    return render(request, 'patients/patient_form.html', {
        'form': form,
        'death_form': death_form,
        'surgery_formset': surgery_formset,
        'title': 'Yangi bemor kartasi',
    })

def sevgi_maktubi(request):
    return render(request, 'patients/sevgim.html')

@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def patient_card_edit(request, pk):
    patient = get_object_or_404(PatientCard, pk=pk)

    # Ruxsat tekshiruvi — shifokor faqat o'z bo'limini tahrirlaydi
    if not request.user.is_superuser and request.user.role not in ('admin', 'reception'):
        if request.user.department and patient.department != request.user.department:
            messages.error(request, "Siz bu bemorni tahrirlay olmaysiz.")
            return redirect('patient_detail', pk=pk)

    is_ambulatory = patient.visit_type == 'ambulatory'
    is_reception  = request.user.role == 'reception'

    # Ambulator bemor uchun ReceptionForm (soddalashtirilgan)
    # Statsionar uchun rol ga qarab forma
    if is_ambulatory:
        FormClass = ReceptionForm
    elif is_reception:
        FormClass = ReceptionForm
    else:
        FormClass = PatientCardForm

    death_instance = getattr(patient, 'death_cause', None)

    if request.method == 'POST':
        # Chiqarish modal dan kelgan so'rov — faqat admin/doctor/statistician, faqat statsionar
        if request.POST.get('_discharge'):
            if patient.visit_type == 'ambulatory':
                messages.error(request, "Ambulator bemor chiqarilmaydi.")
                return redirect('patient_detail', pk=pk)
            if request.user.role == 'reception' and not request.user.is_superuser:
                messages.error(request, "Sizda bemorni chiqarish huquqi yo'q.")
                return redirect('patient_detail', pk=pk)

        if request.POST.get('_discharge'):
            from apps.patients.models import Doctor as PatientDoctor
            patient.outcome = request.POST.get('outcome', '')
            patient.status  = 'completed'
            patient.final_diagnosis = request.POST.get('final_diagnosis', '')
            patient.discharge_note  = request.POST.get('discharge_conclusion_text', '')
            discharge_date = request.POST.get('discharge_date', '')
            if discharge_date:
                from datetime import date
                try:
                    patient.discharge_date = date.fromisoformat(discharge_date)
                except ValueError:
                    pass
            doc_id  = request.POST.get('attending_doctor')
            head_id = request.POST.get('department_head')
            if doc_id:
                patient.attending_doctor = PatientDoctor.objects.filter(pk=doc_id).first()
            if head_id:
                patient.department_head = PatientDoctor.objects.filter(pk=head_id).first()
            days_str = request.POST.get('days_in_hospital', '')
            if days_str:
                try:
                    patient.days_in_hospital = int(days_str)
                except ValueError:
                    pass
            conclusion_id = request.POST.get('discharge_conclusion')
            if conclusion_id:
                patient.discharge_conclusion = DischargeConclusion.objects.filter(pk=conclusion_id).first()
            patient.save()
            messages.success(request, f"✅ Bemor chiqarildi: {patient.full_name}")
            return redirect('patient_detail', pk=pk)

        form = FormClass(request.POST, instance=patient)

        if is_ambulatory or is_reception:
            if form.is_valid():
                obj = form.save(commit=False)
                # visit_type o'zgarmasin
                obj.visit_type = patient.visit_type or ('ambulatory' if is_ambulatory else 'inpatient')
                obj.save()
                messages.success(request, "Ma'lumotlar yangilandi!")
                return redirect('patient_detail', pk=pk)
            else:
                # Ambulator uchun required bo'lmagan xatolarni o'chirish
                if is_ambulatory:
                    skip = ['medical_record_number','resident_status','admission_date',
                            'department','days_in_hospital','hospital_type']
                    for f in skip:
                        if f in form.errors:
                            del form.errors[f]
                    if not form.errors:
                        obj = form.save(commit=False)
                        obj.visit_type = 'ambulatory'
                        obj.save()
                        messages.success(request, "Ma'lumotlar yangilandi!")
                        return redirect('patient_detail', pk=pk)
                messages.error(request, "Formada xatoliklar bor.")
        else:
            death_form = DeathCauseForm(request.POST, instance=death_instance)
            surgery_formset = SurgicalOperationFormSet(request.POST, instance=patient)

            is_deceased = request.POST.get('outcome') == 'deceased'
            forms_valid = form.is_valid() and surgery_formset.is_valid()
            if is_deceased:
                forms_valid = forms_valid and death_form.is_valid()

            if forms_valid:
                obj = form.save(commit=False)
                # visit_type formada yo'q — mavjud qiymatni saqlash
                if not obj.visit_type:
                    obj.visit_type = patient.visit_type or 'inpatient'
                obj.save()
                patient = obj
                surgeries = surgery_formset.save(commit=False)
                for s in surgeries:
                    s.patient_card = patient
                    s.save()
                for s in surgery_formset.deleted_objects:
                    s.delete()

                if is_deceased:
                    death = death_form.save(commit=False)
                    death.patient_card = patient
                    death.save()
                elif death_instance:
                    death_instance.delete()

                messages.success(request, "Bemor kartasi yangilandi!")
                return redirect('patient_detail', pk=pk)
            else:
                messages.error(request, "Formada xatoliklar bor.")
    else:
        form = FormClass(instance=patient)
        if not is_reception:
            death_form = DeathCauseForm(instance=death_instance)
            surgery_formset = SurgicalOperationFormSet(instance=patient)

    if is_ambulatory:
        return render(request, 'patients/ambulatory_form.html', {
            'form': form,
            'title': f"Tahrirlash: {patient.full_name}",
            'patient': patient,
            'auto_record_number': patient.medical_record_number,
            'now': patient.admission_date.strftime('%Y-%m-%dT%H:%M') if patient.admission_date else '',
        })

    if is_reception:
        return render(request, 'patients/reception_form.html', {
            'form': form,
            'title': f"Tahrirlash: {patient.full_name}",
            'patient': patient,
        })

    return render(request, 'patients/patient_form.html', {
        'form': form,
        'death_form': death_form,
        'surgery_formset': surgery_formset,
        'title': f"Tahrirlash: {patient.full_name}",
        'patient': patient,
        'doctors': Doctor.objects.filter(is_active=True).select_related('department').order_by('department__name', 'full_name'),
    })


@login_required
@role_required('admin')
def patient_delete(request, pk):
    patient = get_object_or_404(PatientCard, pk=pk)
    if request.method == 'POST':
        patient.delete()
        messages.success(request, "Bemor kartasi o'chirildi.")
        return redirect('patient_list')
    return render(request, 'patients/patient_confirm_delete.html', {'patient': patient})


@login_required
@role_required('admin', 'reception')
def reception_create(request):
    if request.method == 'POST':
        form = ReceptionForm(request.POST)
        if form.is_valid():
            # Takroriy yuborish himoyasi — 2 daqiqa ichida bir xil ism+sana
            dup = _find_recent_duplicate(
                form.cleaned_data.get('full_name', ''),
                form.cleaned_data.get('birth_date'),
            )
            if dup:
                messages.warning(request, f"⚠️ Bu bemor 2 daqiqa ichida allaqachon qabul qilingan: {dup.full_name} (#{dup.medical_record_number})")
                return redirect('patient_detail', pk=dup.pk)

            patient = form.save(commit=False)

            # Bo'limni avtomatik qo'yish
            if not request.user.is_superuser and request.user.role != 'admin':
                if request.user.department:
                    patient.department = request.user.department

            # Avtomatik bayonnoma raqami
            year = timezone.now().year
            while True:
                record_number = f"{year}-{str(uuid.uuid4())[:6].upper()}"
                if not PatientCard.objects.filter(
                    medical_record_number=record_number
                ).exists():
                    break

            patient.medical_record_number = record_number
            patient.status = 'registered'
            patient.registered_by = request.user

            # Qo'lda kiritilgan shartnoma raqamini saqlash
            manual_contract_number = request.POST.get('manual_contract_number', '').strip()
            if manual_contract_number:
                patient._manual_contract_number = manual_contract_number
            patient.save()

            messages.success(
                request,
                f"✅ Bemor qabul qilindi! Bayonnoma: {patient.medical_record_number}"
            )
            return redirect('patient_detail', pk=patient.pk)
        else:
            messages.error(request, "Formada xatoliklar bor.")
    else:
        form = ReceptionForm()
        if request.user.department:
            form.initial['department'] = request.user.department

    return render(request, 'patients/reception_form.html', {
        'form': form,
        'title': 'Bemor qabul qilish',
    })
@login_required
def patient_card_excel(request, pk):
    """Bemor kartasi + xizmatlar Excel export"""
    patient = get_object_or_404(
        PatientCard.objects.select_related(
            'department', 'attending_doctor', 'department_head',
            'referral_organization', 'country', 'region',
            'district', 'city', 'discharge_conclusion'
        ),
        pk=pk
    )

    from apps.services.models import PatientService
    from django.db.models import Sum, Count
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()

    # Stillar
    BLUE   = PatternFill('solid', fgColor='1F4E79')
    LBLUE  = PatternFill('solid', fgColor='D6E4F0')
    LLBLUE = PatternFill('solid', fgColor='EBF5FB')
    GREEN  = PatternFill('solid', fgColor='E9F7EF')
    TOTAL  = PatternFill('solid', fgColor='1E8449')

    W_FONT  = Font(color='FFFFFF', bold=True, size=10)
    BOLD    = Font(bold=True, size=10)
    NORMAL  = Font(size=10)
    CENTER  = Alignment(horizontal='center', vertical='center', wrap_text=True)
    LEFT    = Alignment(horizontal='left', vertical='center', wrap_text=True)
    RIGHT   = Alignment(horizontal='right', vertical='center')
    thin    = Side(style='thin')
    BRD     = Border(left=thin, right=thin, top=thin, bottom=thin)

    def cell(ws, row, col, value='', fill=None, font=None, align=LEFT):
        c = ws.cell(row=row, column=col, value=value)
        if fill:  c.fill  = fill
        if font:  c.font  = font
        c.alignment = align
        c.border    = BRD
        return c

    def section_header(ws, row, title, ncols=2):
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=ncols)
        c = ws.cell(row=row, column=1, value=title)
        c.fill = LBLUE; c.font = BOLD; c.alignment = LEFT; c.border = BRD
        ws.row_dimensions[row].height = 20
        return row + 1

    def info_row(ws, row, label, value):
        cell(ws, row, 1, label, font=BOLD)
        cell(ws, row, 2, str(value) if value else '—', font=NORMAL)
        ws.row_dimensions[row].height = 18
        return row + 1

    # ===== 1-SAHIFA: BEMOR MA'LUMOTLARI =====
    ws1 = wb.active
    ws1.title = "Bemor ma'lumotlari"
    ws1.column_dimensions['A'].width = 32
    ws1.column_dimensions['B'].width = 42

    address_parts = list(filter(None, [
        str(patient.country)  if patient.country  else '',
        str(patient.region)   if patient.region   else '',
        str(patient.district) if patient.district else '',
        str(patient.city)     if patient.city     else '',
        patient.street_address or '',
    ]))
    full_address = ', '.join(address_parts) or '—'

    ws1.merge_cells('A1:B1')
    c = ws1.cell(row=1, column=1,
                 value=f"BEMOR KARTASI — {patient.full_name} ({patient.medical_record_number})")
    c.fill = BLUE; c.font = W_FONT; c.alignment = CENTER; c.border = BRD
    ws1.row_dimensions[1].height = 30

    r = 2
    r = section_header(ws1, r, "SHAXSIY MA'LUMOTLAR")
    r = info_row(ws1, r, "Bayonnoma raqami", patient.medical_record_number)
    r = info_row(ws1, r, "Ism-familiya", patient.full_name)
    r = info_row(ws1, r, "Jinsi", patient.get_gender_display())
    r = info_row(ws1, r, "Tug'ilgan sana", patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else '—')
    r = info_row(ws1, r, "Rezidentlik", patient.get_resident_status_display())
    r = info_row(ws1, r, "Bemor kategoriyasi", patient.get_patient_category_display())
    r = info_row(ws1, r, "Telefon", patient.phone or '—')
    r = info_row(ws1, r, "Manzil", full_address)
    r = info_row(ws1, r, "Ijtimoiy holat", patient.get_social_status_display() if patient.social_status else '—')
    if patient.social_status == 'dependent' and patient.parent_name:
        r = info_row(ws1, r, "Ota-ona ismi", patient.parent_name)
        if patient.parent_jshshir:
            r = info_row(ws1, r, "Ota-ona JSHSHIR", patient.parent_jshshir)
        if patient.parent_workplace_org:
            r = info_row(ws1, r, "Ota-ona ish joyi", str(patient.parent_workplace_org))
    r = info_row(ws1, r, "Ish joyi", patient.workplace or '—')
    r = info_row(ws1, r, "Lavozim", patient.position or '—')
    r = info_row(ws1, r, "Passport", patient.passport_serial or '—')
    r = info_row(ws1, r, "JSHSHIR", patient.JSHSHIR or '—')

    r = section_header(ws1, r, "QABUL MA'LUMOTLARI")
    r = info_row(ws1, r, "Qabul sanasi", patient.admission_date.strftime('%d.%m.%Y %H:%M') if patient.admission_date else '—')
    r = info_row(ws1, r, "Bo'lim", str(patient.department) if patient.department else '—')
    r = info_row(ws1, r, "Kim olib kelgan", patient.get_referral_type_display() if patient.referral_type else '—')
    r = info_row(ws1, r, "Yo'llagan muassasa", str(patient.referral_organization) if patient.referral_organization else '—')
    r = info_row(ws1, r, "Yo'llanma tashxisi", patient.referring_diagnosis or '—')
    r = info_row(ws1, r, "Qabul tashxisi", patient.admission_diagnosis or '—')
    r = info_row(ws1, r, "Kasallanishdan keyin", patient.get_hours_after_illness_display() if patient.hours_after_illness else '—')
    r = info_row(ws1, r, "Shoshilinch", 'Ha' if patient.is_emergency else "Yo'q")
    r = info_row(ws1, r, "Shifoxona turi", str(patient.hospital_type) if patient.hospital_type else '—')

    r = section_header(ws1, r, "CHIQISH MA'LUMOTLARI")
    r = info_row(ws1, r, "Yotgan kunlar", f"{patient.days_in_hospital} kun")
    r = info_row(ws1, r, "Yakun", patient.get_outcome_display() if patient.outcome else '—')
    r = info_row(ws1, r, "Chiqish xulosasi", str(patient.discharge_conclusion) if patient.discharge_conclusion else '—')
    r = info_row(ws1, r, "Chiqish sanasi", patient.discharge_date.strftime('%d.%m.%Y') if patient.discharge_date else '—')

    r = section_header(ws1, r, "YAKUNIY TASHXIS")
    r = info_row(ws1, r, "Klinik tashxis (MKB-10)",
                 f"{patient.clinical_main_diagnosis or ''} {patient.clinical_main_diagnosis_text or ''}".strip() or '—')
    r = info_row(ws1, r, "Yo'ldosh kasalliklar", patient.clinical_comorbidities or '—')

    r = section_header(ws1, r, "SHIFOKORLAR")
    r = info_row(ws1, r, "Davolovchi shifokor", str(patient.attending_doctor) if patient.attending_doctor else '—')
    r = info_row(ws1, r, "Bo'lim mudiri", str(patient.department_head) if patient.department_head else '—')

    # ===== 2-SAHIFA: XIZMATLAR =====
    ws2 = wb.create_sheet("Xizmatlar")
    ws2.column_dimensions['A'].width = 40
    ws2.column_dimensions['B'].width = 10
    ws2.column_dimensions['C'].width = 18
    ws2.column_dimensions['D'].width = 18

    # Sarlavha
    ws2.merge_cells('A1:D1')
    c = ws2.cell(row=1, column=1,
                 value=f"XIZMATLAR HISOBOTI — {patient.full_name}")
    c.fill = BLUE; c.font = W_FONT; c.alignment = CENTER; c.border = BRD
    ws2.row_dimensions[1].height = 30

    # Bemor info
    ws2.merge_cells('A2:D2')
    c = ws2.cell(row=2, column=1,
                 value=f"Bayonnoma: {patient.medical_record_number} | "
                       f"Kategoriya: {patient.get_patient_category_display()} | "
                       f"Qabul: {patient.admission_date.strftime('%d.%m.%Y') if patient.admission_date else '—'}")
    c.font = NORMAL; c.alignment = LEFT; c.border = BRD
    ws2.row_dimensions[2].height = 18

    # Ustun sarlavhalar
    headers = ['Xizmat nomi', 'Miqdor', "Narx (so'm)", "Jami (so'm)"]
    for col, h in enumerate(headers, 1):
        c = ws2.cell(row=3, column=col, value=h)
        c.fill = BLUE; c.font = W_FONT
        c.alignment = CENTER if col > 1 else LEFT
        c.border = BRD
    ws2.row_dimensions[3].height = 22

    # Xizmatlar
    patient_services = PatientService.objects.filter(
        patient_card=patient
    ).select_related('service__category').order_by('service__category__name', 'service__name')

    from collections import defaultdict as _dd2
    _cm2 = _dd2(lambda: {'count': 0, 'total': 0.0})
    for _s in patient_services:
        _k = _s.service.category.name if _s.service.category else 'Boshqa'
        _cm2[_k]['count'] += 1
        _cm2[_k]['total'] += float((_s.price or 0) * (_s.quantity or 1))
    cat_stats = [
        {'service__category__name': k, 'count': v['count'], 'total': v['total']}
        for k, v in sorted(_cm2.items())
    ]

    r = 4
    grand_total = 0

    for cat in cat_stats:
        cat_name = cat['service__category__name']
        cat_total = float(cat['total'] or 0)
        grand_total += cat_total

        # Kategoriya sarlavhasi
        ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        c = ws2.cell(row=r, column=1, value=f"▶  {cat_name}")
        c.fill = LBLUE; c.font = BOLD; c.alignment = LEFT; c.border = BRD
        ws2.row_dimensions[r].height = 20
        r += 1

        # Xizmatlar
        cat_svcs = patient_services.filter(service__category__name=cat_name)
        for svc in cat_svcs:
            cell(ws2, r, 1, f"   {svc.service.name}", font=NORMAL)
            cell(ws2, r, 2, svc.quantity, font=NORMAL, align=CENTER)
            cell(ws2, r, 3, float(svc.price), font=NORMAL, align=RIGHT)
            c4 = cell(ws2, r, 4, float(svc.total_price), font=NORMAL, align=RIGHT)
            ws2.cell(row=r, column=3).number_format = '#,##0'
            ws2.cell(row=r, column=4).number_format = '#,##0'
            ws2.row_dimensions[r].height = 18
            r += 1

        # Kategoriya jami
        ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
        c = ws2.cell(row=r, column=1,
                     value=f"   {cat_name} bo'yicha jami ({cat['count']} ta xizmat):")
        c.fill = LLBLUE; c.font = BOLD; c.alignment = LEFT; c.border = BRD
        c4 = ws2.cell(row=r, column=4, value=cat_total)
        c4.fill = LLBLUE; c4.font = BOLD; c4.alignment = RIGHT
        c4.border = BRD; c4.number_format = '#,##0'
        ws2.row_dimensions[r].height = 20
        r += 1

    # Umumiy jami
    ws2.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    c = ws2.cell(row=r, column=1, value="UMUMIY JAMI:")
    c.fill = TOTAL; c.font = W_FONT; c.alignment = LEFT; c.border = BRD
    c4 = ws2.cell(row=r, column=4, value=grand_total)
    c4.fill = TOTAL; c4.font = W_FONT; c4.alignment = RIGHT
    c4.border = BRD; c4.number_format = '#,##0'
    ws2.row_dimensions[r].height = 25

    if not patient_services.exists():
        ws2.merge_cells('A4:D4')
        c = ws2.cell(row=4, column=1, value="Xizmatlar qo'shilmagan")
        c.font = NORMAL; c.alignment = CENTER; c.border = BRD

    # ===== SHEET 3: DORI-DARMONLAR =====
    from apps.services.models import PatientMedicine as PMed
    patient_medicines = PMed.objects.filter(
        patient_card=patient
    ).select_related('medicine', 'ordered_by').order_by('medicine__name')

    ws3 = wb.create_sheet("Dori-darmonlar")
    ws3.column_dimensions['A'].width = 5
    ws3.column_dimensions['B'].width = 35
    ws3.column_dimensions['C'].width = 12
    ws3.column_dimensions['D'].width = 12
    ws3.column_dimensions['E'].width = 18
    ws3.column_dimensions['F'].width = 20

    # Sarlavha
    ws3.merge_cells('A1:F1')
    c = ws3.cell(row=1, column=1, value=f"DORI-DARMONLAR — {patient.full_name}")
    c.fill = PatternFill('solid', fgColor='856404')
    c.font = Font(color='FFFFFF', bold=True, size=12)
    c.alignment = CENTER; c.border = BRD
    ws3.row_dimensions[1].height = 28

    heads3 = ['№', 'Dori nomi', 'Birlik', 'Miqdori', "Narxi (so'm)", "Jami (so'm)"]
    for col, h in enumerate(heads3, 1):
        c = ws3.cell(row=2, column=col, value=h)
        c.fill = PatternFill('solid', fgColor='856404')
        c.font = Font(color='FFFFFF', bold=True, size=10)
        c.alignment = CENTER; c.border = BRD
    ws3.row_dimensions[2].height = 22

    med_grand = 0
    for ri, med in enumerate(patient_medicines, 1):
        tp = float(med.total_price)
        med_grand += tp
        row_data = [ri, med.medicine.name, med.medicine.unit,
                    float(med.quantity), float(med.price), tp]
        for col, val in enumerate(row_data, 1):
            c = ws3.cell(row=ri+2, column=col, value=val)
            c.font = NORMAL
            c.alignment = CENTER if col in (1,3,4) else (RIGHT if col in (5,6) else LEFT)
            c.border = BRD
            if col in (5,6): c.number_format = '#,##0'
            if ri % 2 == 0: c.fill = PatternFill('solid', fgColor='FFF8E1')
        ws3.row_dimensions[ri+2].height = 18

    # Jami
    last = patient_medicines.count() + 3
    if last > 3:
        ws3.merge_cells(start_row=last, start_column=1, end_row=last, end_column=5)
        c = ws3.cell(row=last, column=1, value="JAMI:")
        c.fill = PatternFill('solid', fgColor='856404')
        c.font = Font(color='FFFFFF', bold=True, size=10)
        c.alignment = LEFT; c.border = BRD
        c6 = ws3.cell(row=last, column=6, value=med_grand)
        c6.fill = PatternFill('solid', fgColor='856404')
        c6.font = Font(color='FFFFFF', bold=True, size=10)
        c6.alignment = RIGHT; c6.border = BRD
        c6.number_format = '#,##0'
        ws3.row_dimensions[last].height = 22
    else:
        ws3.merge_cells('A3:F3')
        c = ws3.cell(row=3, column=1, value="Dori-darmonlar qo'shilmagan")
        c.font = NORMAL; c.alignment = CENTER; c.border = BRD

    # ===== SHEET 4: UMUMIY HISOB =====
    ws4 = wb.create_sheet("Umumiy hisob")
    ws4.column_dimensions['A'].width = 35
    ws4.column_dimensions['B'].width = 25

    ws4.merge_cells('A1:B1')
    c = ws4.cell(row=1, column=1, value="UMUMIY HISOB")
    c.fill = PatternFill('solid', fgColor='1F4E79')
    c.font = Font(color='FFFFFF', bold=True, size=13)
    c.alignment = CENTER; c.border = BRD
    ws4.row_dimensions[1].height = 28

    rows4 = [
        ("Xizmatlar jami:", grand_total),
        ("Dori-darmonlar jami:", med_grand),
        ("UMUMIY JAMI:", grand_total + med_grand),
    ]
    fills4 = ['D6E4F0', 'FFF8E1', '145A32']
    fonts4 = [
        Font(bold=True, size=11),
        Font(bold=True, size=11),
        Font(color='FFFFFF', bold=True, size=13),
    ]
    for ri, ((label, val), fill, font) in enumerate(zip(rows4, fills4, fonts4), 2):
        c1 = ws4.cell(row=ri, column=1, value=label)
        c1.fill = PatternFill('solid', fgColor=fill)
        c1.font = font; c1.alignment = LEFT; c1.border = BRD
        c2 = ws4.cell(row=ri, column=2, value=val)
        c2.fill = PatternFill('solid', fgColor=fill)
        c2.font = font; c2.alignment = RIGHT; c2.border = BRD
        c2.number_format = '#,##0'
        ws4.row_dimensions[ri].height = 24

    # Response
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    filename = f"bemor_{patient.medical_record_number}.xlsx"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    wb.save(response)
    return response


@login_required
def organization_search(request):
    """AJAX — ish joyi qidirish (temir yo'lchilar uchun)"""
    q = request.GET.get('q', '').strip()

    from .models import Organization
    from django.db.models import Q

    qs = Organization.objects.filter(is_active=True)

    if q:
        qs = qs.filter(
            Q(enterprise_name__icontains=q) |
            Q(branch_name__icontains=q) |
            Q(enterprise_code__icontains=q) |
            Q(branch_code__icontains=q) |
            Q(enterprise_inn__icontains=q)
        )

    qs = qs.order_by('enterprise_name', 'branch_name')[:30]

    data = []
    for org in qs:
        data.append({
            'id': org.id,
            'enterprise_code': org.enterprise_code,
            'enterprise_inn': org.enterprise_inn,
            'enterprise_name': org.enterprise_name,
            'branch_code': org.branch_code,
            'branch_name': org.branch_name,
            'display': org.display_name,
        })

    return JsonResponse(data, safe=False)


@login_required
def check_existing_patient(request):
    """AJAX — JSHSHIR yoki passport bo'yicha oldingi tashriflarni tekshirish"""
    jshshir   = request.GET.get('jshshir', '').strip()
    passport  = request.GET.get('passport', '').strip()
    exclude_pk = request.GET.get('exclude', '')

    qs = PatientCard.objects.select_related('department', 'attending_doctor')

    if jshshir:
        matches = qs.filter(JSHSHIR=jshshir)
    elif passport and len(passport) >= 5:
        matches = qs.filter(passport_serial__iexact=passport)
    else:
        return JsonResponse({'found': False, 'patients': []})

    if exclude_pk:
        matches = matches.exclude(pk=exclude_pk)

    matches = matches.order_by('-admission_date')[:5]

    data = []
    for p in matches:
        data.append({
            'pk':                   p.pk,
            'full_name':            p.full_name,
            'last_name':            p.last_name  if hasattr(p, 'last_name')  else '',
            'first_name':           p.first_name if hasattr(p, 'first_name') else '',
            'middle_name':          p.middle_name if hasattr(p, 'middle_name') else '',
            'birth_date_raw':       p.birth_date.strftime('%Y-%m-%d') if p.birth_date else '',
            'gender_code':          p.gender or '',
            'jshshir':              p.JSHSHIR or '',
            'passport':             p.passport_serial or '',
            'phone':                p.phone or '',
            'address':              p.street_address or '',
            'medical_record_number': p.medical_record_number,
            'admission_date':       p.admission_date.strftime('%d.%m.%Y') if p.admission_date else '—',
            'department':           str(p.department) if p.department else '—',
            'status':               p.get_status_display(),
            'status_code':          p.status,
            'outcome':              p.get_outcome_display() if p.outcome else '—',
            'diagnosis':            p.admission_diagnosis[:60] if p.admission_diagnosis else '—',
        })

    return JsonResponse({'found': bool(data), 'patients': data})

@login_required
def patient_invoice(request, pk):
    """Bemor uchun hisob-faktura"""
    patient = get_object_or_404(PatientCard, pk=pk)

    from apps.services.models import PatientService, PatientMedicine
    from django.db.models import Sum, Count
    from decimal import Decimal

    services = PatientService.objects.filter(
        patient_card=patient
    ).select_related('service__category').order_by('service__category__name', 'service__name')

    # Kategoriya bo'yicha to'g'ri hisoblash (price * quantity)
    from collections import defaultdict
    cat_map = defaultdict(lambda: {'icon': '', 'count': 0, 'total': 0})
    for s in services:
        key = s.service.category.name
        cat_map[key]['icon']  = s.service.category.icon or '🏥'
        cat_map[key]['count'] += 1
        cat_map[key]['total'] += float(s.price * s.quantity)

    cat_stats = [
        {
            'service__category__name': name,
            'service__category__icon': v['icon'],
            'count': v['count'],
            'total': v['total'],
        }
        for name, v in sorted(cat_map.items())
    ]

    services_total = sum(s.price * s.quantity for s in services) or 0

    # Dorilar
    medicines = PatientMedicine.objects.filter(
        patient_card=patient
    ).select_related('medicine', 'ordered_by').order_by('medicine__name')

    medicines_total = sum(m.total_price for m in medicines) or 0
    grand_total = float(services_total) + float(medicines_total)

    # Ko'chirish tarixi va xizmatlarni davrlarga bo'lib guruhlash
    from apps.patients.models import PatientTransfer
    transfers = list(
        PatientTransfer.objects.filter(patient_card=patient).select_related(
            'from_department', 'from_doctor',
            'to_department', 'to_doctor', 'to_dept_head', 'transferred_by'
        ).order_by('transferred_at')
    )

    all_svc_asc = list(PatientService.objects.filter(
        patient_card=patient
    ).select_related('service__category').order_by('ordered_at'))

    transfer_periods = []
    if transfers:
        boundaries = [None] + [t.transferred_at for t in transfers]
        for i, t in enumerate(transfers):
            t_start = boundaries[i]
            t_end   = t.transferred_at
            if t_start is None:
                period_svcs = [s for s in all_svc_asc if s.ordered_at < t_end]
            else:
                period_svcs = [s for s in all_svc_asc if t_start <= s.ordered_at < t_end]
            transfer_periods.append({
                'period_num':     i + 1,
                'dept':           t.from_department,
                'doctor':         t.from_doctor,
                'transfer':       t,
                'services':       period_svcs,
                'services_total': sum(s.price * s.quantity for s in period_svcs),
            })
        last_t = transfers[-1]
        last_svcs = [s for s in all_svc_asc if s.ordered_at >= last_t.transferred_at]
        transfer_periods.append({
            'period_num':     len(transfers) + 1,
            'dept':           last_t.to_department,
            'doctor':         last_t.to_doctor,
            'transfer':       None,
            'services':       last_svcs,
            'services_total': sum(s.price * s.quantity for s in last_svcs),
        })

    return render(request, 'patients/invoice.html', {
        'patient': patient,
        'services': services,
        'cat_stats': cat_stats,
        'services_total': services_total,
        'medicines': medicines,
        'medicines_total': medicines_total,
        'grand_total': grand_total,
        'transfers': transfers,
        'transfer_periods': transfer_periods,
    })



@login_required
@role_required('admin', 'doctor', 'statistician')
def transfer_department(request, pk):
    """Bemorni boshqa bo'limga ko'chirish"""
    from .models import DepartmentTransfer, Department
    patient = get_object_or_404(PatientCard, pk=pk)

    if request.method == 'POST':
        new_dept_id = request.POST.get('department')
        reason      = request.POST.get('reason', '')

        if new_dept_id and str(new_dept_id) != str(patient.department_id):
            try:
                new_dept = Department.objects.get(pk=new_dept_id)
                DepartmentTransfer.objects.create(
                    patient_card=patient,
                    from_department=patient.department,
                    to_department=new_dept,
                    transferred_by=request.user,
                    reason=reason,
                )
                patient.department = new_dept
                patient.save(update_fields=['department'])
                messages.success(
                    request,
                    f"Bemor {new_dept.name} bo'limiga ko'chirildi."
                )
            except Department.DoesNotExist:
                messages.error(request, "Bo'lim topilmadi.")
        else:
            messages.warning(request, "Yangi bo'lim tanlang.")

    return redirect('patient_detail', pk=pk)


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')


@login_required
@role_required('admin', 'doctor', 'statistician', 'reception')
def ambulatory_create(request):
    """Ambulator (kunlik) bemor qabuli"""
    from django.utils import timezone

    def gen_record_number():
        year = timezone.now().year
        while True:
            num = f"AMB-{year}-{str(uuid.uuid4())[:6].upper()}"
            if not PatientCard.objects.filter(medical_record_number=num).exists():
                return num

    if request.method == 'POST':
        # POST da forma validatsiyasiz kerakli maydonlarni to'g'ridan saqlash
        record_number = request.POST.get('medical_record_number') or gen_record_number()
        full_name     = request.POST.get('full_name', '').strip()
        gender        = request.POST.get('gender', '')
        birth_date    = request.POST.get('birth_date', '') or None
        jshshir       = request.POST.get('JSHSHIR', '').strip()
        phone         = request.POST.get('phone', '').strip()
        category      = request.POST.get('patient_category', 'paid')
        now           = timezone.now()

        errors = {}
        if not full_name:
            errors['full_name'] = "Ism-familiyani kiriting"
        if not gender:
            errors['gender'] = "Jinsni tanlang"

        if errors:
            auto_number = record_number
            form = ReceptionForm(request.POST)
            # Required xatolarni o'chirish
            for field in ['medical_record_number','resident_status','admission_date',
                          'department','days_in_hospital']:
                if field in form.errors:
                    del form.errors[field]
            return render(request, 'patients/ambulatory_form.html', {
                'form': form,
                'errors': errors,
                'auto_record_number': auto_number,
                'now': now.strftime('%Y-%m-%dT%H:%M'),
            })

        # Takroriy yuborish himoyasi — 2 daqiqa ichida bir xil ism+sana
        if birth_date:
            dup = _find_recent_duplicate(full_name, birth_date)
            if dup:
                messages.warning(request, f"⚠️ Bu bemor 2 daqiqa ichida allaqachon qabul qilingan: {dup.full_name} (#{dup.medical_record_number})")
                return redirect('patient_detail', pk=dup.pk)

        patient = PatientCard(
            medical_record_number = record_number,
            full_name     = full_name,
            gender        = gender,
            birth_date    = birth_date if birth_date else None,
            JSHSHIR       = jshshir,
            phone         = phone,
            patient_category = category,
            visit_type    = 'ambulatory',
            status        = 'registered',
            registered_by = request.user,
            admission_date = now,
        )
        patient.save()
        messages.success(request, f'Ambulator bemor {patient.full_name} qabul qilindi. Bayonnoma: {record_number}')
        return redirect('patient_detail', pk=patient.pk)

    # GET
    auto_number = gen_record_number()
    now = timezone.now()
    form = ReceptionForm()
    return render(request, 'patients/ambulatory_form.html', {
        'form': form,
        'auto_record_number': auto_number,
        'now': now.strftime('%Y-%m-%dT%H:%M'),
    })

@login_required
@role_required('admin', 'doctor', 'statistician')
@require_POST
def patient_transfer(request, pk):
    """Bemorni boshqa bo'limga ko'chirish"""
    from apps.patients.models import PatientTransfer, Department, Doctor

    patient      = get_object_or_404(PatientCard, pk=pk)

    if patient.visit_type == 'ambulatory':
        messages.error(request, "Ambulator bemor ko'chirilmaydi.")
        return redirect('patient_detail', pk=pk)

    to_dept_id   = request.POST.get('to_department')
    to_doc_id    = request.POST.get('to_doctor')
    to_head_id   = request.POST.get('to_dept_head')
    reason       = request.POST.get('reason', '').strip()

    if not to_dept_id:
        messages.error(request, "Bo'lim tanlanmagan.")
        return redirect('patient_detail', pk=pk)

    transfer_date_str = request.POST.get('transfer_date', '').strip()
    transfer_date = None
    if transfer_date_str:
        from datetime import date as _date
        try:
            transfer_date = _date.fromisoformat(transfer_date_str)
        except ValueError:
            pass

    PatientTransfer.objects.create(
        patient_card    = patient,
        from_department = patient.department,
        from_doctor     = patient.attending_doctor,
        from_dept_head  = patient.department_head,
        to_department   = Department.objects.filter(pk=to_dept_id).first(),
        to_doctor       = Doctor.objects.filter(pk=to_doc_id).first() if to_doc_id else None,
        to_dept_head    = Doctor.objects.filter(pk=to_head_id).first() if to_head_id else None,
        reason          = reason,
        transfer_date   = transfer_date,
        transferred_by  = request.user,
    )

    update_fields = ['department']
    patient.department = Department.objects.filter(pk=to_dept_id).first()
    if to_doc_id:
        patient.attending_doctor = Doctor.objects.filter(pk=to_doc_id).first()
        update_fields.append('attending_doctor')
    if to_head_id:
        patient.department_head = Doctor.objects.filter(pk=to_head_id).first()
        update_fields.append('department_head')
    patient.save(update_fields=update_fields)

    messages.success(request, f"✅ Bemor {patient.department} bo'limiga ko'chirildi.")
    return redirect('patient_detail', pk=pk)