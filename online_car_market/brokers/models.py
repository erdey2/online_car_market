from django.db import models
from online_car_market.users.models import User, Profile

class BrokerProfile(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        SUSPENDED = 'suspended', 'Suspended'

    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='broker_profile')
    national_id = models.CharField(max_length=100, unique=True)
    telebirr_account = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    reviewed_at = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_brokers")
    rejection_reason = models.TextField(blank=True, null=True)

    @property
    def can_post(self):
        return self.status == self.Status.APPROVED

    @property
    def is_verified(self):
        return self.status == self.Status.APPROVED

    def __str__(self):
        return f"{self.profile.first_name} {self.profile.last_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["profile", "national_id"], name="unique_broker_national_id_per_profile"),
        ]

    def get_display_name(self):
        return self.profile.get_full_name()

class BrokerRating(models.Model):
    broker = models.ForeignKey(BrokerProfile, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='broker_ratings')
    rating = models.PositiveIntegerField()  # 1-5 scale
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.rating}/5 for {self.broker.profile.get_full_name()} by {self.user.email}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['broker', 'user'], name='unique_broker_user_rating'),
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name='brokerrating_valid_range'),
        ]
