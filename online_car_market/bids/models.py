from django.db import models
from online_car_market.inventory.models import Car
from django.contrib.auth import get_user_model

User = get_user_model()

class Bid(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid of {self.amount} by {self.user.email} on {self.car}"
