from django.db import models
from online_car_market.users.models import User
from django.urls import reverse

class Dealer(models.Model):
    company_name = models.CharField(max_length=100, db_index=True)
    phone = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100, db_index=True)

    license_number = models.CharField(max_length=50)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    telebirr_account = models.CharField(max_length=100, null=True)
    is_verified = models.BooleanField(default=True) # Dealers are verified by default

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer')

    def __str__(self):
        return f"Dealer: {self.user.email}"

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"pk": self.pk})

class DealerRating(models.Model):
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dealer_ratings')
    rating = models.PositiveIntegerField()  # 1-5 scale
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rating}/5 for {self.dealer.company_name} by {self.user.email}"

    class Meta:
        indexes = [
            models.Index(fields=['dealer'], name='idx_dealerrating_dealer'),
            models.Index(fields=['user'], name='idx_dealerrating_user'),
            models.Index(fields=['dealer', 'user'], name='idx_dealerrating_dealer_user'),
        ]
        constraints = [
            models.UniqueConstraint(fields=['dealer', 'user'], name='unique_dealer_user_rating'),
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name='dealerrating_valid_range'),
        ]
