from django.db import models
from cloudinary.models import CloudinaryField
from django.contrib.auth import get_user_model
from online_car_market.dealers.models import Dealer
from online_car_market.brokers.models import Broker

User = get_user_model()

class CarMake(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class CarModel(models.Model):
    make = models.ForeignKey(CarMake, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.make.name} {self.name}"

    class Meta:
        unique_together = ('make', 'name')
        ordering = ['make__name', 'name']

class Car(models.Model):
    VERIFICATION_STATUSES = [
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('rejected', 'Rejected'),
    ]

    FUEL_TYPES = (
        ('electric', 'Electric'),
        ('hybrid', 'Hybrid'),
        ('petrol', 'Petrol'),
        ('diesel', 'Diesel'),
    )

    STATUS_CHOICES = [
        ('available', 'Available'),
        ('reserved', 'Reserved'),
        ('sold', 'Sold'),
        ('pending_inspection', 'Pending Inspection'),
        ('under_maintenance', 'Under Maintenance'),
        ('delivered', 'Delivered'),
        ('archived', 'Archived'),
    ]

    SALE_TYPES = (
        ('fixed_price', 'Fixed Price'),
        ('auction', 'Auction'),
    )

    make = models.CharField(max_length=100, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    make_ref = models.ForeignKey(CarMake, on_delete=models.SET_NULL, null=True, blank=True, related_name='cars')
    model_ref = models.ForeignKey(CarModel, on_delete=models.SET_NULL, null=True, blank=True, related_name='cars')
    year = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    mileage = models.IntegerField()
    fuel_type = models.CharField(max_length=20, choices=FUEL_TYPES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='available')
    sale_type = models.CharField(max_length=20, choices=SALE_TYPES, default='fixed_price')
    auction_end = models.DateTimeField(null=True, blank=True)  # For auction cars
    dealer = models.ForeignKey(Dealer, on_delete=models.CASCADE, null=True, blank=True, related_name='cars')
    broker = models.ForeignKey(Broker, on_delete=models.CASCADE, null=True, blank=True, related_name='cars')
    posted_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posted_cars')
    verification_status = models.CharField(max_length=20, choices=VERIFICATION_STATUSES, default='pending')
    priority = models.BooleanField(default=False)  # For prioritizing verified cars
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-fill from refs if not provided
        if self.make_ref and not self.make:
            self.make = self.make_ref.name
        if self.model_ref and not self.model:
            self.model = self.model_ref.name
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.make} {self.model} ({self.year})"

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(dealer__isnull=False) | models.Q(broker__isnull=False),
                name='dealer_or_broker_required'
            )
        ]

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

class Bid(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='bids')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Bid of {self.amount} by {self.user.email} on {self.car}"

class Payment(models.Model):
    PAYMENT_TYPES = (
        ('commission', 'Commission'),
        ('purchase', 'Purchase'),
        ('verification_fee', 'Verification Fee'),  # For brokers only
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    transaction_id = models.CharField(max_length=100, unique=True)  # From payment gateway

    def __str__(self):
        return f"{self.payment_type} of {self.amount} by {self.user.email}"



