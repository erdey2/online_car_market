from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from online_car_market.users.models import User, Profile
from rolepermissions.checkers import has_role

class DealerProfile(models.Model):
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='dealer_profile', db_index=True)
    company_name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=50)
    tax_id = models.CharField(max_length=100, null=True, blank=True)
    telebirr_account = models.CharField(max_length=100, null=True)
    is_verified = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

    class Meta:
        ordering = ['company_name']
        indexes = [
            models.Index(fields=['profile'], name='idx_dealerprofile_profile'),
        ]

    def get_display_name(self):
        return self.company_name

class DealerStaff(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='staff_members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dealer_staff_assignments')
    role = models.CharField(
        max_length=20,
        choices=[
            ('seller', 'Seller'),
            ('accountant', 'Accountant'),
            ('hr', 'HR'),
            ('finance', 'Finance'),
        ]
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('dealer', 'user')
        verbose_name = 'Dealer Staff'
        verbose_name_plural = 'Dealer Staff'

    def __str__(self):
        return f"{self.user.email} - {self.role} for {self.dealer.company_name}"


class DealerRating(models.Model):
    dealer = models.ForeignKey(DealerProfile, on_delete=models.CASCADE, related_name='ratings')
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

@receiver(post_save, sender=Profile)
def create_dealer_profile(sender, instance, created, **kwargs):
    if has_role(instance.user, 'dealer'):
        DealerProfile.objects.get_or_create(
            profile=instance,
            defaults={'company_name': instance.user.email, 'license_number': '', 'telebirr_account': ''}
        )
