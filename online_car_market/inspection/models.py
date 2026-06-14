from django.db import models
from django.utils import timezone
from online_car_market.inventory.models import Car
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model

User = get_user_model()

class Inspector(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="inspector_profile"
    )
    company_name = models.CharField(max_length=255)
    license_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_inspectors"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.company_name}"

class Inspection(models.Model):

    STATUS_CHOICES = [
        ("pending", "Pending Verification"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    ]

    CONDITION_CHOICES = [
        ("excellent", "Excellent"),
        ("good", "Good"),
        ("fair", "Fair"),
        ("poor", "Poor"),
    ]

    car = models.ForeignKey(
        Car,
        on_delete=models.CASCADE,
        related_name="inspections"
    )
    inspector = models.ForeignKey(
        Inspector,
        on_delete=models.PROTECT,
        related_name="inspections",
        null=True,
        blank=True
    )

    # Overall inspection score (0–100)
    # Whether mileage is verified
    # Whether accidents were detected
    inspection_score = models.PositiveSmallIntegerField(null=True, blank=True)
    odometer_verified = models.BooleanField(default=False)
    accident_history = models.BooleanField(default=False)
    inspection_date = models.DateField(default=timezone.now)

    remarks = models.TextField(blank=True)
    condition_status = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default="good"
    )
    signed_report = CloudinaryField(
        "signed_report",
        resource_type="auto",
        null=True,
        blank=True
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_inspections"
    )
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    admin_remarks = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_inspections"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-inspection_date"]

        indexes = [
            models.Index(fields=["car"]),
            models.Index(fields=["inspector"]),
            models.Index(fields=["status"]),
            models.Index(fields=["inspection_date"]),
        ]
