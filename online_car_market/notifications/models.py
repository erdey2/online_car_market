from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    verb = models.CharField(max_length=140) # 'booked', 'paid', 'assigned'
    description = models.TextField(blank=True) # optional long text
    data = models.JSONField(default=dict, blank=True) # structured payload
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
        models.Index(fields=['recipient', 'is_read']), models.Index(fields=['created_at']),
        ]

class Device(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    fcm_token = models.CharField(max_length=512)
    platform = models.CharField(max_length=32, choices=(('web','web'),('android','android'),('ios','ios')))
    created_at = models.DateTimeField(auto_now_add=True)

class NotificationPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    email = models.BooleanField(default=True)
    push = models.BooleanField(default=True)
    in_app = models.BooleanField(default=True)
