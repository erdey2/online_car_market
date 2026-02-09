from django.db import models
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model

User = get_user_model()

class Auction(models.Model):
    STATUS_CHOICES = (
        ("scheduled", "Scheduled"),
        ("active", "Active"),
        ("closed", "Closed"),
    )
    car = models.OneToOneField(Car, on_delete=models.CASCADE, related_name="auction")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="scheduled")
    closed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Auction for {self.car}"

class Bid(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["car", "-amount"]),
            models.Index(fields=["car", "-created_at"]),
        ]

    def __str__(self):
        return f"Bid of {self.amount} by {self.user.email} on {self.car}"
