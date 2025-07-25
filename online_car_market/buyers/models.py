from django.db import models
from online_car_market.users.models import User
from online_car_market.inventory.models import Car

# Buyer Profile
class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    contact = models.CharField(max_length=100)
    loyalty_points = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

# Rating
class Rating(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])  # 1-5 stars
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.buyer.username} rated {self.car} ({self.rating})"

# Loyalty Program
class LoyaltyProgram(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    points = models.IntegerField()
    reward = models.CharField(max_length=100, blank=True)  # e.g., "10% discount"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.buyer} - {self.points} points"
