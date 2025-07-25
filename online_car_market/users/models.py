from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

class User(AbstractUser):
    """
    Default custom user model for online-car-market.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = models.CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    role = models.CharField(max_length=50, default='Buyer', choices=[
        ('super_admin', 'Super Admin'),
        ('admin', 'Admin'),
        ('sales', 'Sales'),
        ('accounting', 'Accounting'),
        ('buyer', 'Buyer')
    ])
    description = models.CharField(max_length=100, null=True, blank=True)
    permissions = ArrayField(models.CharField(max_length=100), blank=True, default=list)

class BuyerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='buyer_profile')
    address = models.CharField(max_length=100, null=True, blank=True)
    loyalty_created_at = models.DateTimeField(auto_now_add=True)
    loyalty_score = models.IntegerField()

class BrokerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='broker_profile')
    national_id = models.CharField(max_length=100)
    telebirr_account = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class DealerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dealer_profile')
    name = models.CharField(max_length=100)
    license_number = models.IntegerField()
    address = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
