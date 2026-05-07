# apps/queue_app/urls.py

from django.urls import path
from apps.queue_app import views

urlpatterns = [
    path('display/', views.queue_display, name='queue_display'),
    path('display/data/', views.queue_display_data, name='queue_display_data'),
        # TV ekrani
    path('display/voice/',        views.queue_display_voice,  name='queue_display_voice'),
    # Shifokor paneli
    path('manage/',               views.queue_manage,         name='queue_manage'),
    path('manage/status/',        views.queue_status,         name='queue_status'),
    path('manage/call-next/',     views.queue_call_next,      name='queue_call_next'),
    path('manage/call/<int:pk>/', views.queue_call_specific,  name='queue_call_specific'),
    path('manage/done/<int:pk>/', views.queue_done,           name='queue_done'),
    path('manage/skip/<int:pk>/', views.queue_skip,           name='queue_skip'),
    path('manage/audio-mode/',    views.set_audio_mode,       name='queue_set_audio_mode'),
    # Audio
    path('audio/<int:number>/',   views.generate_queue_audio, name='queue_audio'),
    # Bemor chipta
    path('ticket/<int:pk>/',      views.queue_ticket_view,    name='queue_ticket'),
]