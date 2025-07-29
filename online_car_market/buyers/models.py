from django.db import models
from online_car_market.users.models import User
from online_car_market.inventory.models import Car
from django.urls import reverse

class Buyer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer')
    contact = models.CharField(max_length=100)
    address = models.CharField(max_length=100, null=True, blank=True)
    loyalty_points = models.IntegerField(default=0)
    loyalty_created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Buyer: {self.user.email}"

class Dealer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    address = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dealer: {self.user.email}"

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"pk": self.pk})

class Rating(models.Model):
    buyer = models.ForeignKey(User, on_delete=models.CASCADE)
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    rating = models.IntegerField()
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating by {self.buyer.email} for {self.car}"

class LoyaltyProgram(models.Model):
    buyer = models.ForeignKey(Buyer, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    reward = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Loyalty for {self.buyer.user.email}"

