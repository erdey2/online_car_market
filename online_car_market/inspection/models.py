from django.db import models
from django.utils import timezone
from online_car_market.inventory.models import Car
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model

User = get_user_model()


class Inspection(models.Model):
    STATUS_CHOICES = [('pending', 'Pending Verification'), ('verified', 'Verified'), ('rejected', 'Rejected'),]
    car = models.OneToOneField(Car, on_delete=models.CASCADE, related_name='inspection', help_text="Car being inspected")
    inspected_by = models.CharField(max_length=255, help_text="Garage or company that inspected the car")
    inspection_date = models.DateField(default=timezone.now)
    remarks = models.TextField(blank=True, help_text="Summary of inspection result")
    condition_status = models.CharField(
        max_length=50,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('fair', 'Fair'),
            ('poor', 'Poor'),
        ],
        default='good'
    )
    report_document = CloudinaryField(
        'inspection_report',
        null=True,
        blank=True,
        folder='inspections/reports/',
        allowed_formats=['pdf', 'jpg', 'jpeg', 'png'],
        help_text="Upload the scanned inspection report (PDF or photo)"
    )

    # Workflow fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='verified_inspections')
    verified_at = models.DateTimeField(null=True, blank=True)
    admin_remarks = models.TextField(blank=True, help_text="Remarks by admin during verification")

    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_inspections')
    uploaded_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.report_document and not self.uploaded_at:
            self.uploaded_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspection for {self.car} by {self.inspected_by or 'N/A'}"

    class Meta:
        verbose_name = "Car Inspection"
        verbose_name_plural = "Car Inspections"
