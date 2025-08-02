from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib import admin

class Car(models.Model):
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    mileage = models.IntegerField()
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
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='available')
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



