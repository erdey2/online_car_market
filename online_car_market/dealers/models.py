from django.db import models
from online_car_market.users.models import User
from django.urls import reverse

class Dealer(models.Model):
    company_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=100, null=True, blank=True)
    address = models.CharField(max_length=100)

    license_number = models.CharField(max_length=50)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    telebirr_account = models.CharField(max_length=100, null=True)
    is_verified = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer')

    def __str__(self):
        return f"Dealer: {self.user.email}"

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"pk": self.pk})
