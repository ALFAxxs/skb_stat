# apps/queue/views.py

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from apps.queue_app.models import QueueTicket
from apps.patients.models import PatientCard
from apps.services.models import PatientService, ServiceCategory


# MRT kategoriyasi ID ni settings dan yoki dinamik olish
MRT_CATEGORY_NAMES = ['MRT', 'mrt', 'МРТ', 'Rengen MRT', 'Rentgen/UZI/MRT']


def get_mrt_category_ids():
    """Barcha MRT kategoriyalarining ID larini qaytaradi"""
    from django.db.models import Q
    q = Q()
    for name in MRT_CATEGORY_NAMES:
        q |= Q(name__iexact=name)
    return list(ServiceCategory.objects.filter(q).values_list('id', flat=True))

def get_mrt_category():
    for name in MRT_CATEGORY_NAMES:
        cat = ServiceCategory.objects.filter(name__iexact=name).first()
        if cat:
            return cat
    return None


# ===== 0. AUDIO GENERATSIYA =====

def generate_queue_audio(request, number):
    """Navbat raqami uchun audio fayl yaratish — gTTS bilan"""
    import os, hashlib
    from django.http import FileResponse, HttpResponse
    from django.conf import settings

    try:
        from gtts import gTTS
    except ImportError:
        return HttpResponse("gTTS o'rnatilmagan", status=500)

    lang = request.GET.get('lang', 'ru')
    cache_dir = os.path.join(settings.MEDIA_ROOT, 'queue_audio')
    os.makedirs(cache_dir, exist_ok=True)

    # Matn
    # O'zbek raqam so'zlari (rus harflarida - gTTS ru engine to'g'ri o'qiydi)
    UZ_NUMS = ['', 'бир', 'икки', 'уч', 'тўрт', 'беш', 'олти', 'етти',
               'саккиз', 'тўqqиз', 'ўн', 'ўн бир', 'ўн икки', 'ўн уч',
               'ўн тўрт', 'ўн беш', 'ўн олти', 'ўн етти', 'ўн саккиз',
               'ўн тўqqиз', 'йигирма', 'йигирма бир', 'йигирма икки',
               'йигирма уч', 'йигирма тўрт', 'йигирма беш', 'йигирма олти',
               'йигирма етти', 'йигирма саккиз', 'йигирма тўqqиз', 'ўттиз',
               'ўттиз бир', 'ўттиз икки', 'ўттиз уч', 'ўттиз тўрт', 'ўттиз беш',
               'ўттиз олти', 'ўттиз етти', 'ўттиз саккиз', 'ўттиз тўqqиз', 'қирқ',
               'қирқ бир', 'қирқ икки', 'қирқ уч', 'қирқ тўрт', 'қирқ беш',
               'қирқ олти', 'қирқ етти', 'қирқ саккиз', 'қирқ тўqqиз', 'эллик']

    num_word_ru = ''
    num_word_uz = UZ_NUMS[number] if number < len(UZ_NUMS) else str(number)

    if lang == 'uz':
        text = f"Навбат рақами {num_word_uz}. Марҳамат қилинг."
        tts_lang = 'ru'
    else:
        text = f"Талон номер {number}. Пожалуйста пройдите."
        tts_lang = 'ru'

    # Cache fayl nomi
    fname = f"queue_{number}_{lang}.mp3"
    fpath = os.path.join(cache_dir, fname)

    # Agar cache da yo'q bo'lsa yaratish
    if not os.path.exists(fpath):
        try:
            tts = gTTS(text=text, lang=tts_lang, slow=False)
            tts.save(fpath)
        except Exception as e:
            return HttpResponse(f"Audio xato: {e}", status=500)

    return FileResponse(open(fpath, 'rb'), content_type='audio/mpeg')


# ===== 1. NAVBAT EKRANI (TV/Monitor) =====

def queue_display(request):
    """Zalda ko'rsatiladigan navbat ekrani — login kerak emas"""
    return render(request, 'queue/display.html')


def queue_display_data(request):
    """Polling uchun JSON — har 3 soniyada yangilanadi"""
    current = QueueTicket.current_calling()
    today   = timezone.now().date()

    waiting = list(QueueTicket.objects.filter(
        created_at__date=today,
        status='waiting'
    ).order_by('ticket_number').values('ticket_number', 'room')[:10])

    # Oxirgi 5 ta yakunlangan
    recent_done = list(QueueTicket.objects.filter(
        created_at__date=today,
        status='done'
    ).order_by('-done_at').values('ticket_number')[:5])

    return JsonResponse({
        'current': {
            'number': current.ticket_number if current else None,
            'room':   current.room if current else None,
            'name':   current.patient_card.full_name if current else None,
        },
        'waiting':     waiting,
        'recent_done': recent_done,
        'total_waiting': len(waiting),
    })


# ===== 2. SHIFOKOR PANELI =====

@login_required
def queue_manage(request):
    """Shifokor navbatni boshqaradi"""
    today   = timezone.now().date()
    waiting = QueueTicket.objects.filter(
        created_at__date=today,
        status='waiting'
    ).order_by('ticket_number').select_related('patient_card')

    calling = QueueTicket.objects.filter(
        created_at__date=today,
        status='calling'
    ).select_related('patient_card').first()

    done_count = QueueTicket.objects.filter(
        created_at__date=today,
        status='done'
    ).count()

    return render(request, 'queue/manage.html', {
        'waiting':    waiting,
        'calling':    calling,
        'done_count': done_count,
        'today':      today,
    })


@login_required
@require_POST
def queue_call_next(request):
    """Keyingi bemorni chaqirish"""
    today = timezone.now().date()

    # Hozirgi chaqirilayotganni 'serving' ga o'tkazish
    QueueTicket.objects.filter(status='calling').update(
        status='serving', served_at=timezone.now()
    )

    # Keyingi kutayotganni olish
    next_ticket = QueueTicket.objects.filter(
        created_at__date=today,
        status='waiting'
    ).order_by('ticket_number').first()

    if not next_ticket:
        return JsonResponse({'success': False, 'message': 'Navbatda hech kim yo\'q'})

    next_ticket.status    = 'calling'
    next_ticket.called_at = timezone.now()
    next_ticket.save()

    return JsonResponse({
        'success': True,
        'number':  next_ticket.ticket_number,
        'room':    next_ticket.room,
        'name':    next_ticket.patient_card.full_name,
    })


@login_required
@require_POST
def queue_call_specific(request, pk):
    """Aniq raqamli bemorni chaqirish"""
    ticket = get_object_or_404(QueueTicket, pk=pk)

    QueueTicket.objects.filter(status='calling').update(
        status='serving', served_at=timezone.now()
    )

    ticket.status    = 'calling'
    ticket.called_at = timezone.now()
    ticket.save()

    return JsonResponse({
        'success': True,
        'number':  ticket.ticket_number,
        'room':    ticket.room,
        'name':    ticket.patient_card.full_name,
    })


@login_required
@require_POST
def queue_done(request, pk):
    """Xizmat yakunlandi"""
    ticket = get_object_or_404(QueueTicket, pk=pk)
    ticket.status  = 'done'
    ticket.done_at = timezone.now()
    ticket.save()
    return JsonResponse({'success': True})


@login_required
@require_POST
def queue_skip(request, pk):
    """O'tkazib yuborish"""
    ticket = get_object_or_404(QueueTicket, pk=pk)
    ticket.status = 'skipped'
    ticket.save()
    return JsonResponse({'success': True})


# ===== 3. NAVBAT HOLATI (polling uchun) =====

@login_required
def queue_status(request):
    """Shifokor paneli uchun polling"""
    today = timezone.now().date()

    calling = QueueTicket.objects.filter(status='calling').first()
    waiting = list(QueueTicket.objects.filter(
        created_at__date=today, status='waiting'
    ).order_by('ticket_number').values(
        'id', 'ticket_number', 'room',
        'patient_card__full_name'
    ))

    return JsonResponse({
        'calling': {
            'id':     calling.pk if calling else None,
            'number': calling.ticket_number if calling else None,
            'name':   calling.patient_card.full_name if calling else None,
        },
        'waiting': waiting,
        'waiting_count': len(waiting),
    })


# ===== 4. CHIPTA YARATISH (PatientService saqlanganda) =====

def create_queue_ticket(patient_service):
    """MRT xizmati qo'shilganda navbat chipta yaratish.
    Qoida: Bir bemor kunda faqat 1 ta aktiv navbatga ega bo'ladi.
    """
    # MRT kategoriyami tekshirish
    mrt_ids = get_mrt_category_ids()
    if not mrt_ids:
        return None
    if patient_service.service.category_id not in mrt_ids:
        return None

    today = timezone.now().date()

    # Bemorda bugun AKTIV navbat bormi?
    # done yoki skipped bo'lmagan navbat mavjud bo'lsa — yangisini yaratmaymiz
    existing = QueueTicket.objects.filter(
        patient_card=patient_service.patient_card,
        created_at__date=today,
    ).exclude(status__in=['done', 'skipped']).first()

    if existing:
        # Mavjud navbatni qaytaramiz (yangi yaratmaymiz)
        return existing

    # Yangi navbat yaratish
    ticket = QueueTicket.objects.create(
        ticket_number=QueueTicket.next_ticket_number(),
        patient_card=patient_service.patient_card,
        service=patient_service,
        status='waiting',
        room='MRT xonasi',
    )
    return ticket


# ===== 5. CHIPTA KO'RISH =====

def queue_ticket_view(request, pk):
    """Bemor o'z chiptasini ko'radi"""
    ticket = get_object_or_404(QueueTicket, pk=pk)
    today  = timezone.now().date()

    # Oldindagi navbat soni
    ahead = QueueTicket.objects.filter(
        created_at__date=today,
        status='waiting',
        ticket_number__lt=ticket.ticket_number
    ).count()

    return render(request, 'queue/ticket.html', {
        'ticket': ticket,
        'ahead':  ahead,
    })