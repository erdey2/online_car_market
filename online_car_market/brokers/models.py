from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from online_car_market.users.models import User, Profile
from rolepermissions.checkers import has_role

class BrokerProfile(models.Model):
    national_id = models.CharField(max_length=100, unique=True)
    telebirr_account = models.CharField(max_length=100)
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='broker_profile')
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.profile.first_name} {self.profile.last_name}"

    class Meta:
        indexes = [
            models.Index(fields=['profile'], name='idx_brokerprofile_profile'),
            models.Index(fields=['national_id'], name='idx_brokerprofile_national_id'),
        ]

class BrokerRating(models.Model):
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broker_ratings')
    rating = models.PositiveIntegerField()  # 1-5 scale
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rating}/5 for {self.profile.first_name} {self.profile.last_name} by {self.user.email}"

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

@receiver(post_save, sender=Profile)
def create_broker_profile(sender, instance, created, **kwargs):
    if has_role(instance.user, 'broker'):
        BrokerProfile.objects.get_or_create(
            profile=instance,
            defaults={'national_id': f"ID_{instance.user.id}", 'telebirr_account': ''}
        )
