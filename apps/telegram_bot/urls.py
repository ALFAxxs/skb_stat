from django.urls import path
from .views import (
    VerifyPatientView, CheckBindingView,
    PatientResultsView, ResultDetailView,
    ResultPdfView, UpdateTelegramFileIdView,
    NotificationSeenView,
    PriceListView, BotConfigView, UpdateLanguageView,
)

urlpatterns = [
    # Auth
    path('verify/',                          VerifyPatientView.as_view()),
    path('binding/',                         CheckBindingView.as_view()),

    # Results
    path('results/',                         PatientResultsView.as_view()),
    path('results/<int:pk>/',                ResultDetailView.as_view()),
    path('results/<int:pk>/pdf/',            ResultPdfView.as_view()),
    path('results/<int:pk>/file-id/',        UpdateTelegramFileIdView.as_view()),

    # Notifications
    path('notifications/<int:pk>/seen/',     NotificationSeenView.as_view()),

    # Info
    path('prices/',                          PriceListView.as_view()),
    path('config/',                          BotConfigView.as_view()),
    path('language/',                        UpdateLanguageView.as_view()),
]