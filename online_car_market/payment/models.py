from django.db import models
from online_car_market.brokers.models import BrokerProfile
from django.utils import timezone

class Payment(models.Model):
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')
    transaction_id = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return f"Payment {self.transaction_id} for {self.broker} - {self.status}"

    def save(self, *args, **kwargs):
        if self.status == 'completed':
            self.broker.can_post = True
            self.broker.save()
        super().save(*args, **kwargs)
