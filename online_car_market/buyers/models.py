from django.db import models
from online_car_market.users.models import User

class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    contact = models.CharField(max_length=100)
    address = models.CharField(max_length=100, null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    loyalty_created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buyer: {self.user.email}"

class LoyaltyProgram(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    reward = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loyalty for {self.buyer.user.email}"

