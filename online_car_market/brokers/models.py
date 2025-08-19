from django.db import models
from online_car_market.users.models import User
from online_car_market.inventory.models import Car

class Broker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker')
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2)  # e.g., 5.00 for 5%
    national_id = models.CharField(max_length=100, unique=True)
    telebirr_account = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Broker: {self.name} ({self.user.email})"

class BrokerListing(models.Model):
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    commission = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.broker.name} - {self.car}"

    class Meta:
        unique_together = ('broker', 'car')
