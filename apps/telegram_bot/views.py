from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from apps.patients.models import PatientCard
from apps.laboratory.models import LabResult
from apps.services.models import Service

from .models import (
    TelegramUser, PatientTelegramBinding,
    ResultNotification, ResultFile, AuditLog, BotConfig,
)
from .permissions import IsBotService
from .serializers import (
    LabResultListSerializer, LabResultDetailSerializer,
    ServicePriceSerializer,
)


def _normalize_phone(phone: str) -> str:
    digits = ''.join(c for c in phone if c.isdigit())
    if digits.startswith('998'):
        digits = digits[3:]
    return digits[-9:] if len(digits) >= 9 else digits


def _get_patient_for_user(telegram_id: int):
    """Telegram ID bo'yicha asosiy bemor kartasi va user ni qaytarish."""
    try:
        binding = PatientTelegramBinding.objects.select_related(
            'patient_card', 'telegram_user'
        ).get(
            telegram_user__telegram_id=telegram_id,
            status='verified',
        )
        return binding.patient_card, binding.telegram_user
    except PatientTelegramBinding.DoesNotExist:
        return None, None


def _get_all_patients_for_user(telegram_id: int):
    """
    Telefon raqami bo'yicha barcha PatientCard larni qaytarish.
    Bir bemor bir necha marta ro'yxatdan o'tgan bo'lsa ham barchasini topadi.
    """
    try:
        binding = PatientTelegramBinding.objects.select_related(
            'telegram_user'
        ).get(
            telegram_user__telegram_id=telegram_id,
            status='verified',
        )
        tg_user = binding.telegram_user
        phone   = binding.bound_phone  # normalize qilingan 9 raqam

        patients = list(PatientCard.objects.filter(phone__endswith=phone))
        if not patients:
            patients = [
                p for p in PatientCard.objects.exclude(phone='').only('pk', 'phone')
                if _normalize_phone(p.phone) == phone
            ]
            if patients:
                patients = list(PatientCard.objects.filter(pk__in=[p.pk for p in patients]))

        return patients, tg_user
    except PatientTelegramBinding.DoesNotExist:
        return [], None


# ══════════════════════════════════════════════════════
# AUTH
# ══════════════════════════════════════════════════════

class VerifyPatientView(APIView):
    """
    POST /api/bot/verify/
    Bot orqali telefon raqami bilan bemorni tekshirish va bog'lash.
    """
    permission_classes = [IsBotService]

    def post(self, request):
        telegram_id = request.data.get('telegram_id')
        phone_raw   = request.data.get('phone', '')

        if not telegram_id or not phone_raw:
            return Response({'found': False, 'error': 'telegram_id va phone majburiy'}, status=400)

        phone = _normalize_phone(phone_raw)

        # TelegramUser topish yoki yaratish
        tg_user, _ = TelegramUser.objects.update_or_create(
            telegram_id=telegram_id,
            defaults={
                'phone':      phone,
                'first_name': request.data.get('first_name', ''),
                'last_name':  request.data.get('last_name', ''),
                'username':   request.data.get('username', ''),
            }
        )

        if tg_user.is_blocked:
            AuditLog.write(telegram_id, 'blocked', {'reason': 'user is blocked'}, tg_user)
            return Response({'found': False, 'blocked': True})

        # PatientCard da telefon qidirish — avval tez yo'l, keyin normalize solishtirish
        patient = PatientCard.objects.filter(phone__endswith=phone).first()

        if not patient:
            for p in PatientCard.objects.exclude(phone='').only('pk', 'phone'):
                if _normalize_phone(p.phone) == phone:
                    patient = PatientCard.objects.get(pk=p.pk)
                    break

        if not patient:
            AuditLog.write(telegram_id, 'auth_fail', {'phone': phone}, tg_user)
            return Response({'found': False})

        # Bog'lash
        PatientTelegramBinding.objects.update_or_create(
            telegram_user=tg_user,
            defaults={
                'patient_card': patient,
                'status':       'verified',
                'bound_phone':  phone,
            }
        )
        tg_user.is_verified = True
        tg_user.save(update_fields=['is_verified'])

        AuditLog.write(telegram_id, 'auth', {'patient_id': patient.pk}, tg_user)

        return Response({
            'found':         True,
            'full_name':     patient.full_name,
            'record_number': patient.medical_record_number,
            'patient_id':    patient.pk,
            'gender':        patient.gender,
            'birth_date':    patient.birth_date.strftime('%d.%m.%Y') if patient.birth_date else '',
        })


class CheckBindingView(APIView):
    """GET /api/bot/binding/?telegram_id=<id>"""
    permission_classes = [IsBotService]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')
        if not telegram_id:
            return Response({'bound': False})

        try:
            binding = PatientTelegramBinding.objects.select_related(
                'patient_card', 'telegram_user'
            ).get(
                telegram_user__telegram_id=telegram_id,
                status='verified',
            )
            tg = binding.telegram_user
            if tg.is_blocked:
                return Response({'bound': False, 'blocked': True})
            return Response({
                'bound':         True,
                'full_name':     binding.patient_card.full_name,
                'patient_id':    binding.patient_card.pk,
                'gender':        binding.patient_card.gender,
                'language':      tg.language_code,
                'telegram_user_id': tg.pk,
            })
        except PatientTelegramBinding.DoesNotExist:
            return Response({'bound': False})


# ══════════════════════════════════════════════════════
# LAB RESULTS
# ══════════════════════════════════════════════════════

class PatientResultsView(APIView):
    """
    GET /api/bot/results/?telegram_id=<id>
    Faqat o'z natijalari.
    """
    permission_classes = [IsBotService]

    def get(self, request):
        telegram_id = request.query_params.get('telegram_id')
        patients, tg_user = _get_all_patients_for_user(telegram_id)

        if not patients:
            return Response({'error': 'Unauthorized'}, status=403)

        results = LabResult.objects.filter(
            patient_card__in=patients,
            status__in=['verified', 'printed'],
        ).select_related('template').order_by('-created_at')

        AuditLog.write(int(telegram_id), 'view_results', {}, tg_user)

        serializer = LabResultListSerializer(results, many=True)
        return Response(serializer.data)


class ResultDetailView(APIView):
    """GET /api/bot/results/<pk>/?telegram_id=<id>"""
    permission_classes = [IsBotService]

    def get(self, request, pk):
        telegram_id = request.query_params.get('telegram_id')
        patients, tg_user = _get_all_patients_for_user(telegram_id)

        if not patients:
            return Response({'error': 'Unauthorized'}, status=403)

        try:
            result = LabResult.objects.select_related(
                'template', 'created_by', 'verified_by'
            ).prefetch_related(
                'values__parameter__group'
            ).get(pk=pk, patient_card__in=patients)
        except LabResult.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        AuditLog.write(int(telegram_id), 'view_result', {'result_id': pk}, tg_user)

        serializer = LabResultDetailSerializer(
            result, context={'gender': result.patient_card.gender}
        )
        return Response(serializer.data)


# ══════════════════════════════════════════════════════
# PDF
# ══════════════════════════════════════════════════════

class ResultPdfView(APIView):
    """GET /api/bot/results/<pk>/pdf/?telegram_id=<id>"""
    permission_classes = [IsBotService]

    def get(self, request, pk):
        from datetime import timedelta
        from django.utils import timezone

        telegram_id = request.query_params.get('telegram_id')
        patients, tg_user = _get_all_patients_for_user(telegram_id)

        if not patients:
            return Response({'error': 'Unauthorized'}, status=403)

        try:
            result = LabResult.objects.get(pk=pk, patient_card__in=patients)
        except LabResult.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)

        # ResultFile mavjud bo'lmasa yoki muddati o'tgan bo'lsa — yaratish
        pdf_file = getattr(result, 'pdf_file', None)
        if not pdf_file:
            pdf_file = ResultFile.objects.create(
                lab_result=result,
                expires_at=timezone.now() + timedelta(days=30),
            )
        elif pdf_file.is_expired:
            pdf_file.expires_at = timezone.now() + timedelta(days=30)
            pdf_file.save(update_fields=['expires_at'])

        AuditLog.write(int(telegram_id), 'download_pdf', {'result_id': pk}, tg_user)

        return Response({
            'ready':        True,
            'secure_token': pdf_file.secure_token,
        })


class UpdateTelegramFileIdView(APIView):
    """
    POST /api/bot/results/<pk>/file-id/
    Bot PDF yuborib Telegram file_id ni saqlaydi.
    """
    permission_classes = [IsBotService]

    def post(self, request, pk):
        file_id = request.data.get('telegram_file_id', '')
        try:
            pdf = ResultFile.objects.get(lab_result_id=pk)
            pdf.telegram_file_id = file_id
            pdf.save(update_fields=['telegram_file_id'])
            return Response({'ok': True})
        except ResultFile.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)


# ══════════════════════════════════════════════════════
# NOTIFICATION
# ══════════════════════════════════════════════════════

class NotificationSeenView(APIView):
    """POST /api/bot/notifications/<pk>/seen/"""
    permission_classes = [IsBotService]

    def post(self, request, pk):
        try:
            notif = ResultNotification.objects.get(pk=pk)
            notif.mark_seen()
            return Response({'ok': True})
        except ResultNotification.DoesNotExist:
            return Response({'error': 'Not found'}, status=404)


# ══════════════════════════════════════════════════════
# PRICE LIST
# ══════════════════════════════════════════════════════

class PriceListView(APIView):
    """GET /api/bot/prices/?category=<id>&q=<search>"""
    permission_classes = [IsBotService]

    def get(self, request):
        qs = Service.objects.select_related('category').filter(
            is_active=True,
        ).order_by('category__name', 'name')

        q = request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(name__icontains=q)

        cat_id = request.query_params.get('category')
        if cat_id:
            qs = qs.filter(category_id=cat_id)

        from apps.services.models import ServiceCategory
        categories = ServiceCategory.objects.filter(
            is_active=True
        ).values('id', 'name', 'category_type').order_by('name')

        return Response({
            'categories': list(categories),
            'services':   ServicePriceSerializer(qs[:100], many=True).data,
        })


# ══════════════════════════════════════════════════════
# BOT CONFIG
# ══════════════════════════════════════════════════════

class BotConfigView(APIView):
    """GET /api/bot/config/"""
    permission_classes = [IsBotService]

    def get(self, request):
        cfg = BotConfig.get()
        return Response({
            'welcome_uz':    cfg.welcome_uz,
            'welcome_ru':    cfg.welcome_ru,
            'welcome_en':    cfg.welcome_en,
            'about_uz':      cfg.about_uz,
            'about_ru':      cfg.about_ru,
            'contacts':      cfg.contacts,
            'working_hours': cfg.working_hours,
            'is_maintenance': cfg.is_maintenance,
            'maintenance_msg': cfg.maintenance_msg,
        })


# ══════════════════════════════════════════════════════
# LANGUAGE UPDATE
# ══════════════════════════════════════════════════════

class UpdateLanguageView(APIView):
    """POST /api/bot/language/ — foydalanuvchi tilini o'zgartirish"""
    permission_classes = [IsBotService]

    def post(self, request):
        telegram_id = request.data.get('telegram_id')
        lang        = request.data.get('language', 'uz')
        if lang not in ('uz', 'ru', 'en'):
            lang = 'uz'
        updated = TelegramUser.objects.filter(
            telegram_id=telegram_id
        ).update(language_code=lang)
        return Response({'ok': bool(updated)})
