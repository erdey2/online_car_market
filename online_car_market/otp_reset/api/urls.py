from django.urls import path
from .views import RequestPasswordResetOTP, ConfirmPasswordResetOTP

urlpatterns = [
    path('request/', RequestPasswordResetOTP.as_view(), name='reset-request'),
    path('confirm/', ConfirmPasswordResetOTP.as_view(), name='reset-confirm'),
]
