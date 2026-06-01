from rest_framework.permissions import BasePermission
from django.conf import settings


class IsBotService(BasePermission):
    """
    Faqat bot service so'rovlariga ruxsat.
    Header: X-Bot-Secret: <TELEGRAM_BOT_SECRET>
    """
    def has_permission(self, request, view):
        secret = request.headers.get('X-Bot-Secret', '')
        return secret == settings.TELEGRAM_BOT_SECRET