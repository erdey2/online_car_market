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

    class Meta:
        ordering = ['name']

class BrokerRating(models.Model):
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broker_ratings')
    rating = models.PositiveIntegerField()  # 1-5 scale
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rating}/5 for {self.broker.name} by {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['broker'], name='idx_brokerrating_broker'),
            models.Index(fields=['user'], name='idx_brokerrating_user'),
            models.Index(fields=['broker', 'user'], name='idx_brokerrating_broker_user'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['broker', 'user'], name='unique_broker_user_rating'),
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name='brokerrating_valid_range'),
        ]
