from django.db import models
from online_car_market.inventory.models import Car
from online_car_market.users.models import User
from online_car_market.brokers.models import BrokerProfile

class Sale(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE)
    buyer = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='purchases')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    broker = models.ForeignKey(BrokerProfile, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"Sale of {self.car} on {self.date}"

class Lead(models.Model):
    name = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)  # Email or phone
    status = models.CharField(max_length=50, choices=[
        ('inquiry', 'Inquiry'),
        ('negotiation', 'Negotiation'),
        ('closed', 'Closed')
    ], default='inquiry')
    assigned_sales = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='leads')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.status}"
