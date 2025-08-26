from django.db import models
from online_car_market.users.models import User

class Broker(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    national_id = models.CharField(max_length=100, unique=True)
    telebirr_account = models.CharField(max_length=100)

    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker')

    def __str__(self):
        return f"Broker: {self.name} ({self.user.email})"
