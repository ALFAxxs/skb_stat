# apps/contracts/tasks.py

import logging

from celery import shared_task
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_contract_pdf_task(self, contract_pk: int):
    """Shartnoma PDF sini fon jarayonda yaratadi va saqlaydi."""
    try:
        from apps.contracts.models import Contract
        from apps.contracts.utils import generate_contract_pdf

        contract = Contract.objects.get(pk=contract_pk)
        if contract.pdf_file:
            return  # Allaqachon mavjud

        pdf_bytes = generate_contract_pdf(contract)
        filename = f"contract_{contract.contract_number}.pdf"
        contract.pdf_file.save(filename, ContentFile(pdf_bytes), save=True)
        logger.info(f"Contract PDF yaratildi: {filename}")

    except Exception as exc:
        logger.error(f"Contract #{contract_pk} PDF xatosi: {exc}")
        raise self.retry(exc=exc)
