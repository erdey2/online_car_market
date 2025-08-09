from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model
from online_car_market.dealers.models import Dealer
from django.utils.translation import gettext_lazy as _

User = get_user_model()

class Car(models.Model):
    VERIFICATION_STATUSES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    fuel_type = models.CharField(max_length=50, choices=[
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel')
    ])

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('pending_inspection', 'Pending Inspection'),
        ('under_maintenance', 'Under Maintenance'),
        ('delivered', 'Delivered'),
        ('archived', 'Archived'),
    ]
    brand = models.CharField(max_length=255, null=True, blank=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mileage = models.IntegerField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='available')
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE)
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_cars')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUSES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year})"

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('image')  # stores the Cloudinary image reference
    is_featured = models.BooleanField(default=False)
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.car} (Featured: {self.is_featured})"

    def save(self, *args, **kwargs):
        if self.is_featured:
            # Set is_featured=False for all other images of this car
            CarImage.objects.filter(car=self.car, is_featured=True).exclude(pk=self.pk).update(is_featured=False)
        super().save(*args, **kwargs)



