from django.apps import AppConfig
from django.conf import settings


class DmedSyncConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name  = 'apps.dmed_sync'
    label = 'dmed_sync'
    verbose_name = 'DMED Sinxronizatsiya'

    def ready(self):
        # Signals
        from .signals import connect_signals
        connect_signals()

        # Background worker — faqat asosiy jarayon uchun (runserver / gunicorn)
        # Test va migrate jarayonlarida ishga tushirmaylik
        import sys
        is_manage = 'manage.py' in sys.argv[0] if sys.argv else False
        skip_cmds = {'migrate', 'makemigrations', 'collectstatic', 'shell',
                     'test', 'check', 'createsuperuser'}
        running_cmd = sys.argv[1] if len(sys.argv) > 1 else ''

        dmed_enabled = getattr(settings, 'DMED_SYNC_ENABLED', False)
        if dmed_enabled and running_cmd not in skip_cmds:
            from .worker import start
            start()
