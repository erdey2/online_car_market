from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL

class Advertisement(models.Model):
    AD_TARGET_CHOICES = (
        ("car", "Car"),
        ("broker", "Broker Profile"),
        ("dealer", "Dealer Profile"),
        ("service", "Service"),
    )
    OWNER_TYPE_CHOICES = (
        ("broker", "Broker"),
        ("dealer", "Dealer"),
    )
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
    )
    owner_type = models.CharField(max_length=20, choices=OWNER_TYPE_CHOICES)
    owner_id = models.PositiveIntegerField()

    target_type = models.CharField(max_length=20, choices=AD_TARGET_CHOICES)
    target_id = models.PositiveIntegerField()

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='ads/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    views = models.PositiveIntegerField(default=0)
    clicks = models.PositiveIntegerField(default=0)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def is_active_now(self):
        if self.status != 'active':
            return False
        if self.end_date and self.end_date < timezone.now():
            self.status = 'expired'
            self.save(update_fields=['status'])
            return False
        return True

    def __str__(self):
        return f"Ad by {self.created_by} - {self.AD_TARGET_CHOICES[self.target_type]}"

