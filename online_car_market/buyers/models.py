from django.db import models
from online_car_market.users.models import User, Profile

class BuyerProfile(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='buyer_profile')
    loyalty_points = models.PositiveIntegerField(default=0, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buyer profile for {self.profile.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['profile'], name='idx_buyerprofile_profile'),
        ]

class LoyaltyProgram(models.Model):
    buyer = models.ForeignKey(BuyerProfile, on_delete=models.CASCADE, related_name='loyalty_programs')
    points = models.IntegerField(default=0)
    reward = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loyalty for {self.buyer.profile.user.email}"

