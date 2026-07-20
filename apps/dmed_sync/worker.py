"""
Background worker — har 10 soniyada pending DMED sync yozuvlarini qayta ishlaydi.
Django app tayyor bo'lgach avtomatik ishga tushadi (apps.py → ready()).
"""
import logging
import threading
import time

logger = logging.getLogger('dmed_sync')

_worker_thread: threading.Thread | None = None
_stop_event = threading.Event()

POLL_INTERVAL = 10   # sekund — navbatni qancha vaqtda bir tekshirish


def _loop():
    logger.info('DMED sync worker ishga tushdi')
    while not _stop_event.is_set():
        try:
            from .tasks import run_pending
            run_pending()
        except Exception as exc:
            logger.exception(f'DMED sync worker xato: {exc}')
        _stop_event.wait(timeout=POLL_INTERVAL)
    logger.info('DMED sync worker to\'xtatildi')


def start():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _stop_event.clear()
    _worker_thread = threading.Thread(target=_loop, daemon=True, name='dmed-sync-worker')
    _worker_thread.start()


def stop():
    _stop_event.set()
