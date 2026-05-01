# apps/contracts/views.py

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile

from apps.contracts.models import Contract
from apps.contracts.utils import generate_contract_pdf


@login_required
def download_contract(request, pk):
    """Shartnomani PDF ko'rinishida yuklab olish"""
    contract = get_object_or_404(Contract, pk=pk)

    # PDF yo'q bo'lsa qayta generatsiya qilish
    if not contract.pdf_file:
        try:
            pdf_bytes = generate_contract_pdf(contract)
            filename = f"contract_{contract.contract_number}.pdf"
            contract.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        except Exception as e:
            return HttpResponse(f"PDF generatsiya xatosi: {e}", status=500)

    # PDF faylni qaytarish
    try:
        pdf_content = contract.pdf_file.read()
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="shartnoma_{contract.contract_number}.pdf"'
        )
        return response
    except Exception:
        # Fayl topilmasa qayta generatsiya
        pdf_bytes = generate_contract_pdf(contract)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="shartnoma_{contract.contract_number}.pdf"'
        )
        return response


@login_required
def regenerate_contract(request, pk):
    """Shartnoma PDFini qayta generatsiya qilish"""
    contract = get_object_or_404(Contract, pk=pk)
    try:
        pdf_bytes = generate_contract_pdf(contract)
        filename = f"contract_{contract.contract_number}.pdf"
        if contract.pdf_file:
            contract.pdf_file.delete(save=False)
        contract.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        from django.contrib import messages
        messages.success(request, "✅ Shartnoma PDF qayta yaratildi.")
    except Exception as e:
        from django.contrib import messages
        messages.error(request, f"Xato: {e}")
    from django.shortcuts import redirect
    return redirect('patient_detail', pk=contract.patient_card.pk)


def verify_contract(request, token):
    """QR kod orqali shartnomani tekshirish — login talab qilinmaydi"""
    contract = get_object_or_404(Contract, verify_token=token)
    patient = contract.patient_card

    # Maxfiylik uchun ism qisqartiriladi
    name_parts = patient.full_name.split()
    if len(name_parts) >= 2:
        short_name = f"{name_parts[0]} {name_parts[1][0]}."
        if len(name_parts) >= 3:
            short_name = f"{name_parts[0]} {name_parts[1][0]}. {name_parts[2][0]}."
    else:
        short_name = patient.full_name

    return render(request, 'contracts/verifiy.html', {
        'contract': contract,
        'short_name': short_name,
    })


def download_contract_public(request, token):
    """QR kod orqali PDF yuklab olish — login talab qilinmaydi"""
    contract = get_object_or_404(Contract, verify_token=token)

    if not contract.pdf_file:
        from apps.contracts.utils import generate_contract_pdf
        from django.core.files.base import ContentFile
        try:
            pdf_bytes = generate_contract_pdf(contract)
            filename = f"contract_{contract.contract_number}.pdf"
            contract.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        except Exception as e:
            return HttpResponse(f"PDF generatsiya xatosi: {e}", status=500)

    try:
        pdf_content = contract.pdf_file.read()
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="shartnoma_{contract.contract_number}.pdf"'
        )
        return response
    except Exception:
        from apps.contracts.utils import generate_contract_pdf
        pdf_bytes = generate_contract_pdf(contract)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = (
            f'inline; filename="shartnoma_{contract.contract_number}.pdf"'
        )
        return response