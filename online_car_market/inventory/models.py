from django.db import models
from django.contrib.postgres.fields import ArrayField


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
    images = ArrayField(models.URLField(), blank=True, default=list)  # URLs to Digital Ocean Spaces
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year})"
