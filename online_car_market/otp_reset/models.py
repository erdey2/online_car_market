from django.db import models
from django.utils import timezone
from django.conf import settings

class PasswordResetOTP(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        app_label = 'otp_reset'

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(minutes=10)
