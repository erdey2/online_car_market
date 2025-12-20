from django.db import models
from online_car_market.inventory.models import Car
from online_car_market.users.models import User

class CarRating(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='car_ratings')
    rating = models.PositiveIntegerField()  # 1–5
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            # One rating per user per car
            models.UniqueConstraint(fields=['car', 'user'], name='unique_car_user_rating'),
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name='carrating_valid_range'),
        ]
        indexes = [
            models.Index(fields=['car']),
            models.Index(fields=['user']),
            models.Index(fields=['car', 'user']),
        ]

    def __str__(self):
        return f"{self.rating}/5 for {self.car} by {self.user.email}"

